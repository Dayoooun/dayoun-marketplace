# -*- coding: utf-8 -*-
"""codex 병렬 이미지 생성 하네스 (v3) — ima2 병렬 개념을 codex로 복제 + 상태격리 + 재귀개선 루프.

ima2 서버·OAuth 로그인 없이, 이미 인증된 codex(GPT Image)로 여러 슬라이드를 동시 생성한다.

핵심 설계(전부 실전 사고의 교훈 내장):
  1) 세션당 base_dir 하위 ASCII 격리 폴더 — %TEMP% 금지(codex Windows 샌드박스 split-root 거부)
  2) ★★ 잡별 CODEX_HOME 격리 — codex 세션이 ~/.codex 공유 상태(cap_sid 등)로 서로 내용을 섞는
     "고병렬 오염" 방지. auth.json+config.toml만 격리홈에 복사 → 고병렬에서도 안전
  3) codex 경로를 Windows 셰임과 macOS Homebrew 대표 경로에서 자동 탐색
  4) 검증: 스타일앵커 필수(철칙B) + 이미지생성 강제(철칙A) + 파일<60KB=코드드로잉 불합격
     + ★중복 헤드라인 해시=내용오염 검출
  5) ★재귀 개선 루프(--loop N): 실패/오염 잡만 재생성, 전부 통과할 때까지 반복
  6) 고품질: --effort(reasoning) / --model / 프롬프트 고해상도 지시

사용:
  python codex_parallel_gen.py jobs.json --cap 10 --retry 1 --loop 4 --effort high
  jobs.json = [{"label","refs":[...],"out","prompt"}]  (경로는 jobs.json 기준 상대/절대)
  refs = 스타일 앵커(필수). 원하는 룩의 완성 슬라이드를 넣는다.
         부트스트랩 1장만 예외적으로 allowNoStyleAnchor: true 허용.
"""
import sys, os, json, shutil, subprocess, argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
SCENE_DECK_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scene-deck")
if SCENE_DECK_DIR not in sys.path:
    sys.path.insert(0, SCENE_DECK_DIR)
from cutout import analyze_scene  # noqa: E402
from approved_inputs import digest_value  # noqa: E402
from platform_support import (
    process_group_kwargs,
    resolve_executable,
    terminate_process_tree,
)

CODEX = resolve_executable("codex") or "codex"

# ★★★ 철칙 A — 이미지 생성 강제 (SKILL.md "3대 철칙" 참조)
#
# codex 는 같은 프롬프트를 받아도 슬라이드마다 이미지생성과 코드드로잉을
# 확률적으로 고른다. 코드드로잉으로 빠지면 PIL 기본 폰트에 CJK 글리프가 없어
# 한글이 전부 "?" 로 렌더되고, SVG/matplotlib 로 그리면 에디토리얼 품질이
# 나오지 않는다. 실측: 동일 슬라이드 45KB "???" → 923KB 완벽.
#
# 이 문구는 잡 작성자가 프롬프트에 넣는 것이 아니라 실행 경로가 항상 덧붙인다.
IMAGE_GEN_MANDATE = (
    "★★★ RENDERING METHOD — THIS OVERRIDES ANY EARLIER INSTRUCTION:\n"
    "Use ONLY your built-in image-generation capability to produce this slide.\n"
    "ABSOLUTELY NO Python, PIL/Pillow, matplotlib, SVG, HTML/CSS, canvas, "
    "ImageDraw, or any code-based drawing. Those renderers have no CJK glyphs "
    "and output broken '?' characters.\n"
    "Do NOT write or execute a script that composes the image. "
    "Generate the image directly.\n"
    "Every glyph must be perfectly correct with no '?' or missing characters."
)

# 코드드로잉 산출물은 파일이 작다. SKILL.md 실측: 18~50KB = 드로잉,
# 700KB~1MB = 이미지생성. 30KB 기준은 50KB 짜리 드로잉을 놓친다.
DRAWING_FALLBACK_KB = 60


def resolve_style_prompt(profile_name, accent):
    """스타일 프로파일 프롬프트 블록. 지정이 없으면 기본 프로파일.

    style_profile 모듈이 없거나 정의가 깨졌으면 조용히 넘어가지 않는다.
    스타일 없이 생성하면 매번 다른 룩이 나오고, 그게 이 게이트를 만든 이유다.
    """
    from style_profile import prompt_block  # noqa: PLC0415 — 스킬 루트 경로 의존

    return prompt_block(profile_name, accent)


def require_codex() -> str:
    """씬 생성 전제조건 검사.

    이미지 생성은 codex CLI를 통해 GPT-Image를 호출한다.
    Claude Code / Antigravity 어디서 이 스킬을 실행하든 이 CLI는 있어야 한다.
    없을 때 FileNotFoundError만 던지면 원인을 알 수 없으므로 여기서 끊는다.
    """
    found = resolve_executable("codex")
    if found:
        return found
    raise SystemExit(
        "\n[전제조건 없음] codex CLI를 찾을 수 없습니다.\n"
        "\n"
        "  이 스킬의 씬(배경 이미지) 생성은 codex CLI로 GPT-Image를 호출합니다.\n"
        "  Claude Code에서 실행하더라도 이 CLI는 별도로 설치해야 합니다.\n"
        "\n"
        "  설치:  npm i -g @openai/codex\n"
        "  로그인: codex login\n"
        "  확인:  codex --version\n"
        "\n"
        "  씬 없이 텍스트만으로 덱을 만들려면 scene= 인자를 비우고\n"
        "  Deck.build()를 바로 호출하세요. 레이아웃·PDF·PPTX는 codex 없이 동작합니다.\n"
    )
BASE_FLAGS = ["exec", "-s", "workspace-write", "--skip-git-repo-check"]
USER_CODEX_HOME = os.path.join(os.path.expanduser("~"), ".codex")


def _ascii_id(job, idx):
    stem = os.path.splitext(os.path.basename(job.get("out", f"job{idx}")))[0]
    slug = "".join(c if (c.isascii() and (c.isalnum() or c in "_-")) else "" for c in stem)
    return slug or f"job{idx}"


def _scene_background(image):
    from PIL import ImageStat

    width, height = image.size
    patch = max(2, min(width, height) // 50)
    corners = (
        image.crop((0, 0, patch, patch)),
        image.crop((width - patch, 0, width, patch)),
        image.crop((0, height - patch, patch, height)),
        image.crop((width - patch, height - patch, width, height)),
    )
    channels = list(zip(*(ImageStat.Stat(corner).median for corner in corners)))
    return tuple(int(sum(values) / len(values)) for values in channels)


def scene_safe_zone_receipt(path, margin=0.18):
    from PIL import Image, ImageChops

    if not 0 < margin < 0.5:
        raise ValueError("scene safe-zone margin must be between 0 and 0.5")
    with Image.open(path) as opened:
        original = opened.copy()
    analysis = analyze_scene(path)
    if analysis["backgroundMode"] == "transparent-alpha":
        alpha = original.convert("RGBA").getchannel("A")
        box = alpha.point(lambda value: 255 if value > 8 else 0).getbbox()
    else:
        image = original.convert("RGB")
        background = _scene_background(image)
        background_image = Image.new("RGB", image.size, background)
        difference = ImageChops.difference(image, background_image).convert("L")
        mask = difference.point(lambda value: 255 if value > 14 else 0)
        box = mask.getbbox()
    if box is None:
        return {
            "status": "BLOCK",
            "margin": margin,
            "safeMargin": margin,
            "error": "scene contains no detectable foreground",
        }
    left, top, right, bottom = box
    width, height = original.size
    margins = {
        "left": left / width,
        "top": top / height,
        "right": (width - right) / width,
        "bottom": (height - bottom) / height,
    }
    passed = all(value >= margin - 0.005 for value in margins.values())
    return {
        "status": "PASS" if passed else "BLOCK",
        "margin": margin,
        "safeMargin": margin,
        "generatedCanvas": [width, height],
        "foregroundBox": [left, top, right, bottom],
        "contentBBox": analysis["contentBBox"] or [left, top, right, bottom],
        "contentCoverage": analysis["contentCoverage"],
        "backgroundMode": analysis["backgroundMode"],
        "alpha": analysis["alpha"],
        "checkerboardDetected": analysis["checkerboardDetected"],
        "analysisErrors": analysis["errors"],
        "margins": margins,
        "sha256": analysis["sha256"],
    }


def frame_scene_safe_zone(path, margin=0.18):
    from PIL import Image

    with Image.open(path) as opened:
        image = opened.copy()
    width, height = image.size
    scale = 1.0 - 2.0 * margin
    target = (
        max(1, int(round(width * scale))),
        max(1, int(round(height * scale))),
    )
    resized = image.resize(target, Image.Resampling.LANCZOS)
    alpha = image.convert("RGBA").getchannel("A")
    has_transparency = alpha.getextrema()[0] < 255
    if has_transparency:
        resized = resized.convert("RGBA")
        canvas = Image.new("RGBA", image.size, (0, 0, 0, 0))
        offset = ((width - target[0]) // 2, (height - target[1]) // 2)
        canvas.alpha_composite(resized, dest=offset)
    else:
        image = image.convert("RGB")
        resized = resized.convert("RGB")
        canvas = Image.new("RGB", image.size, _scene_background(image))
        canvas.paste(resized, ((width - target[0]) // 2, (height - target[1]) // 2))
    canvas.save(path, format="PNG", optimize=True)
    receipt = scene_safe_zone_receipt(path, margin)
    if receipt["status"] != "PASS":
        raise ValueError(f"scene safe-zone framing failed: {receipt}")
    return receipt


def write_scene_safe_receipt(path, receipt):
    sidecar = str(path) + ".safe.json"
    with open(sidecar, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(receipt, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def _iso_home(work):
    """잡별 격리 CODEX_HOME 생성 — 공유 세션상태 오염 차단. auth+config만 복사."""
    home = os.path.join(work, ".codexhome")
    os.makedirs(home, exist_ok=True)
    for fn in ("auth.json", "config.toml"):
        src = os.path.join(USER_CODEX_HOME, fn)
        if os.path.exists(src):
            shutil.copy(src, os.path.join(home, fn))
    return home


def _run_one(job, base_dir, retry, idx=0, effort=None, model=None, timeout=590):
    """단일 codex 생성 잡 (격리 폴더 + 격리 CODEX_HOME에서 실행)."""
    prompt = job["prompt"]
    refs = [os.path.join(base_dir, r) if not os.path.isabs(r) else r for r in job.get("refs", [])]
    # ★ 철칙 B 강제 (SKILL.md "3대 철칙").
    # 스타일 앵커 없이 프롬프트만 주면 모델이 매번 다른 룩을 만든다. "토스 느낌"
    # 같은 지시는 프롬프트 문장으로 재현되지 않는다 — 원하는 룩의 완성 덱을
    # `-i` 로 먹여야 고정된다. 앵커가 없으면 조용히 앙상한 기본 룩으로 빠지므로
    # 여기서 끊고 부트스트랩(1장 뽑아 고른 뒤 앵커로 재사용)을 요구한다.
    if not refs and not job.get("allowNoStyleAnchor"):
        raise ValueError(
            f"[{job.get('label', 'job')}] 스타일 앵커가 없습니다. "
            "원하는 룩의 완성 슬라이드를 refs 에 넣으세요. "
            "레퍼런스가 아직 없으면 표지 1장을 여러 변형으로 뽑아 사용자가 고른 것을 "
            "이후 슬라이드의 앵커로 재사용하고, 그 부트스트랩 1장에만 "
            "allowNoStyleAnchor: true 를 붙이세요."
        )
    missing_refs = [r for r in refs if not os.path.isfile(r)]
    if missing_refs:
        raise FileNotFoundError(
            f"[{job.get('label', 'job')}] 스타일 앵커 파일이 없습니다: {missing_refs}"
        )
    out = job["out"] if os.path.isabs(job["out"]) else os.path.join(base_dir, job["out"])
    os.makedirs(os.path.dirname(out), exist_ok=True)
    aid = _ascii_id(job, idx)
    label = job.get("label", aid)

    for attempt in range(retry + 1):
        work = os.path.join(base_dir, ".cxwork", f"{aid}_{attempt}")
        shutil.rmtree(work, ignore_errors=True)
        os.makedirs(work, exist_ok=True)
        try:
            local_refs = []
            for r in refs:
                dst = os.path.join(work, os.path.basename(r))
                shutil.copy(r, dst)
                local_refs.append(os.path.basename(r))
            result_name = "__out.png"
            cmd = [CODEX] + BASE_FLAGS
            if effort:
                cmd += ["-c", f'model_reasoning_effort="{effort}"']
            if model:
                cmd += ["-m", model]
            for lr in local_refs:
                cmd += ["-i", lr]
            # ★ 철칙 A 강제 (SKILL.md "3대 철칙"). 프롬프트에 이미지생성 강제가 없으면
            # codex 가 슬라이드를 Python/PIL/matplotlib 로 그려버린다. PIL 기본 폰트에는
            # CJK 글리프가 없어 모든 한글이 "?" 로 렌더된다. 문서에만 적어 두면 잡 작성자가
            # 빠뜨리므로 실행 경로에서 무조건 덧붙인다.
            # ★ 스타일 프로파일 강제. 산문 설명만 두면 매 실행 다른 룩이 나온다.
            # 잡이 지정하지 않으면 style_profiles.json 의 기본값(modern-flat)을 쓴다.
            style_block = resolve_style_prompt(
                job.get("styleProfile"), job.get("accentColor")
            )
            full_prompt = (
                prompt
                + "\n\n"
                + style_block
                + "\n\n"
                + IMAGE_GEN_MANDATE
                + f"\n\n결과를 반드시 {result_name} (파일명 정확히) 로 저장하고 크기를 출력하라."
            )
            env = dict(os.environ, CODEX_HOME=_iso_home(work))  # ★상태 격리
            # ★★ 캐시 즉시 반환 (2026-07-14): 이미지가 나타나는 순간 회수하고 codex 트리 강제종료.
            #    codex는 생성 후 후처리/요약에 수백 초 매달림 — 블로킹 대기는 순수 낭비 (검증: ppt-image-first bubu_genAB)
            import glob as _glob
            import time as _time
            proc = subprocess.Popen(
                cmd, cwd=work, stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                text=True, encoding="utf-8", errors="replace", env=env,
                **process_group_kwargs(),
            )
            try:
                proc.stdin.write(full_prompt)
                proc.stdin.close()
            except OSError:
                pass
            result_path = os.path.join(work, result_name)
            cache_pat = os.path.join(work, ".codexhome", "generated_images", "**", "*.png")
            deadline = _time.time() + timeout
            produced = None
            _last = {}
            cache_stable_at = None
            while _time.time() < deadline:
                if os.path.exists(result_path):          # 정식 산출물(정확한 크기) 최우선
                    produced = result_path
                    break
                cands = _glob.glob(cache_pat, recursive=True)
                if cands:
                    newest = max(cands, key=os.path.getmtime)
                    sz = os.path.getsize(newest)
                    if sz > 100_000 and _last.get(newest) == sz:  # 크기 2연속 동일 = 쓰기 완료
                        if cache_stable_at is None:
                            cache_stable_at = _time.time()
                        # 캐시 확보 후 __out.png(리사이즈본) 대기 (2026-08-01 G002: 45s→12s).
                        # 캐시본은 이미 원본 해상도라 리사이즈본을 오래 기다릴 이유가 없다.
                        # 실측: 45초 대기 중 __out.png가 추가로 나온 비율 <10%.
                        if _time.time() - cache_stable_at > 12:
                            produced = newest
                            break
                    _last[newest] = sz
                if proc.poll() is not None:              # codex 자연 종료 → 마지막 스캔
                    if os.path.exists(result_path):
                        produced = result_path
                    elif cands:
                        produced = max(cands, key=os.path.getmtime)
                    break
                # 적응형 폴링(2026-08-01 G002): 초반 0.6s로 촘촘히 → 이미지 즉시 회수.
                # 고정 3초는 잡당 평균 1.5초를 그냥 버린다.
                _elapsed = _time.time() - (deadline - timeout)
                _time.sleep(0.6 if _elapsed < 90 else (1.5 if _elapsed < 240 else 3))
            # codex 트리 강제 종료 (매달림 제거) — Windows/macOS 공통
            terminate_process_tree(proc)
            if produced is None:
                produced = os.path.join(work, result_name)
            if not os.path.exists(produced):
                pngs = [os.path.join(work, f) for f in os.listdir(work)
                        if f.lower().endswith(".png") and f not in [os.path.basename(x) for x in local_refs]]
                if pngs:
                    produced = max(pngs, key=os.path.getmtime)
            if not os.path.exists(produced):
                # ★ no-output 플레이키 회수: codex가 저장은 건너뛰어도 격리홈 캐시엔 생성본이 남는다
                import glob as _glob
                cache = _glob.glob(os.path.join(work, ".codexhome", "generated_images", "**", "*.png"), recursive=True)
                if cache:
                    produced = max(cache, key=os.path.getmtime)
            if os.path.exists(produced):
                shutil.copy(produced, out)
                source_artifact = str(out) + ".source.png"
                shutil.copyfile(out, source_artifact)
                scene_mode = job.get("scene_mode", "cutout")
                requested_transparent = bool(
                    job.get("requested_transparent", False)
                )
                pre_frame_report = analyze_scene(
                    source_artifact,
                    requested_transparent=requested_transparent,
                )
                if scene_mode == "cutout" and pre_frame_report["status"] != "PASS":
                    raise ValueError(
                        "generated cutout or alpha validation failed before framing: "
                        + "; ".join(pre_frame_report["errors"])
                    )
                safe_receipt = None
                safe_zone = job.get("safe_zone")
                if safe_zone is not None:
                    margin = float(safe_zone)
                    if job.get("safe_frame", False):
                        safe_receipt = frame_scene_safe_zone(out, margin)
                    else:
                        safe_receipt = scene_safe_zone_receipt(out, margin)
                    if safe_receipt["status"] != "PASS":
                        raise ValueError(f"scene violates the safe zone: {safe_receipt}")
                    content_report = analyze_scene(
                        out,
                        requested_transparent=requested_transparent,
                    )
                    if scene_mode == "cutout" and content_report["status"] != "PASS":
                        raise ValueError(
                            "scene cutout or alpha validation failed: "
                            + "; ".join(content_report["errors"])
                        )
                    safe_receipt.update(
                        {
                            "sceneMode": scene_mode,
                            "transparencyRequested": requested_transparent,
                            "contentBBox": content_report["contentBBox"],
                            "contentCoverage": content_report["contentCoverage"],
                            "backgroundMode": content_report["backgroundMode"],
                            "alpha": content_report["alpha"],
                            "checkerboardDetected": content_report[
                                "checkerboardDetected"
                            ],
                            "contentErrors": content_report["errors"],
                            "sourceArtifact": os.path.basename(source_artifact),
                            "sourceSha256": pre_frame_report["sha256"],
                            "preFrameContentBBox": pre_frame_report["contentBBox"],
                            "preFrameBackgroundMode": pre_frame_report["backgroundMode"],
                            "jobPromptDigest": digest_value(job["prompt"]),
                        }
                    )
                    write_scene_safe_receipt(out, safe_receipt)
                size_kb = os.path.getsize(out) // 1024
                # ★ 철칙 A 검출. SKILL.md 실측: 코드드로잉 18~50KB / 이미지생성 700KB~1MB.
                # 30KB 기준은 50KB 짜리 드로잉을 통과시킨다. 60KB 로 올린다.
                status = (
                    f"WARN(코드드로잉의심<{DRAWING_FALLBACK_KB}KB)"
                    if size_kb < DRAWING_FALLBACK_KB
                    else "OK"
                )
                # WARN 을 내고도 그대로 반환하면 재시도 기회를 버린다.
                # 남은 시도가 있으면 다시 뽑는다 — verify 가 같은 기준으로 불합격 처리한다.
                if size_kb < DRAWING_FALLBACK_KB and attempt < retry:
                    continue
                return {
                    "label": label,
                    "status": status,
                    "out": out,
                    "size_kb": size_kb,
                    "attempt": attempt + 1,
                    "safeZone": safe_receipt,
                }
        except subprocess.TimeoutExpired:
            if attempt == retry:
                return {"label": label, "status": "FAIL(timeout)", "out": out}
        except Exception as e:
            if attempt == retry:
                return {"label": label, "status": f"FAIL({type(e).__name__})", "out": out}
        finally:
            shutil.rmtree(work, ignore_errors=True)
    return {"label": label, "status": "FAIL(no-output)", "out": out}


def _ahash_head(path, hsize=16):
    """슬라이드 상단(헤드라인) 영역 average-hash — 중복(내용오염) 검출용."""
    try:
        from PIL import Image
        im = Image.open(path).convert("L")
        W, H = im.size
        strip = im.crop((0, 0, W, int(H * 0.22))).resize((hsize, hsize))
        # Pillow 14(2027-10)에서 Image.getdata()가 제거된다.
        # get_flattened_data()가 후속 API이나 12.x에는 없으므로 폴백을 둔다.
        if hasattr(strip, "get_flattened_data"):
            px = list(strip.get_flattened_data())
        else:
            px = list(strip.getdata())
        avg = sum(px) / len(px)
        return sum(1 << i for i, p in enumerate(px) if p > avg)
    except Exception:
        return None


def _hamming(a, b):
    return bin(a ^ b).count("1") if (a is not None and b is not None) else 999


def _verify_scene_artifacts(out, job, margin):
    mode = job.get("scene_mode", "cutout")
    requested_transparent = bool(job.get("requested_transparent", False))
    current = analyze_scene(
        out,
        requested_transparent=requested_transparent,
    )
    if mode == "cutout" and current["status"] != "PASS":
        return "cutout-validation(" + ";".join(current["errors"]) + ")"
    sidecar_path = str(out) + ".safe.json"
    try:
        with open(sidecar_path, encoding="utf-8") as handle:
            receipt = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return "safe-receipt-missing-or-invalid"
    safe_current = scene_safe_zone_receipt(out, float(margin))
    if not all(receipt.get(key) == value for key, value in safe_current.items()):
        return "safe-receipt-stale"
    if receipt.get("sceneMode") != mode:
        return "safe-receipt-mode-mismatch"
    if bool(receipt.get("transparencyRequested")) != requested_transparent:
        return "safe-receipt-transparency-mismatch"
    if receipt.get("jobPromptDigest") != digest_value(job.get("prompt", "")):
        return "safe-receipt-prompt-mismatch"
    source_path = str(out) + ".source.png"
    if (
        receipt.get("sourceArtifact") != os.path.basename(source_path)
        or not os.path.isfile(source_path)
        or os.path.islink(source_path)
    ):
        return "unframed-source-missing-or-noncanonical"
    source = analyze_scene(
        source_path,
        requested_transparent=requested_transparent,
    )
    if mode == "cutout" and source["status"] != "PASS":
        return "unframed-source-validation(" + ";".join(source["errors"]) + ")"
    if (
        receipt.get("sourceSha256") != source["sha256"]
        or receipt.get("preFrameContentBBox") != source["contentBBox"]
        or receipt.get("preFrameBackgroundMode") != source["backgroundMode"]
        or receipt.get("contentBBox") != current["contentBBox"]
        or receipt.get("backgroundMode") != current["backgroundMode"]
        or receipt.get("alpha") != current["alpha"]
        or receipt.get("checkerboardDetected") != current["checkerboardDetected"]
    ):
        return "scene-source-or-content-receipt-stale"
    return None


def verify(jobs, base_dir, dup_check=False):
    """실패/오염 잡 라벨 반환. 크기<60KB(코드드로잉 폴백) 검출.
    ⚠️ dup-headline은 기본 OFF: CODEX_HOME 격리가 내용오염을 이미 차단하므로 중복. 게다가
    에디토리얼 덱은 상단 여백+헤드라인 위치가 유사해 avg-hash가 닮아 '오염'으로 오탐 → 불필요 재생성.
    옛 draft-anchor 파이프라인(격리 없이 고병렬)에서만 --dup-check로 켤 것.
    ★ 어느 검사도 '한글 글자 깨짐'은 못 잡는다 → 반드시 사람 눈/비전으로 컨택트시트 검수."""
    bad = {}
    hashes = {}
    for j in jobs:
        out = j["out"] if os.path.isabs(j["out"]) else os.path.join(base_dir, j["out"])
        lbl = j.get("label", out)
        if not os.path.exists(out):
            bad[lbl] = "missing"; continue
        if os.path.getsize(out) < DRAWING_FALLBACK_KB * 1024:
            bad[lbl] = f"code-drawing-fallback(<{DRAWING_FALLBACK_KB}KB)"; continue
        safe_zone = j.get("safe_zone")
        if safe_zone is not None:
            try:
                receipt = scene_safe_zone_receipt(out, float(safe_zone))
            except Exception as error:
                bad[lbl] = f"safe-zone-error({type(error).__name__})"
                continue
            if receipt["status"] != "PASS":
                bad[lbl] = "safe-zone-violation"
                continue
            try:
                artifact_error = _verify_scene_artifacts(out, j, safe_zone)
            except Exception as error:
                bad[lbl] = f"scene-artifact-error({type(error).__name__})"
                continue
            if artifact_error is not None:
                bad[lbl] = artifact_error
                continue
        hashes[lbl] = _ahash_head(out)
    if dup_check:
        labels = list(hashes)
        for i in range(len(labels)):
            for k in range(i + 1, len(labels)):
                if _hamming(hashes[labels[i]], hashes[labels[k]]) <= 6:
                    bad.setdefault(labels[i], "dup-headline(오염)")
                    bad.setdefault(labels[k], "dup-headline(오염)")
    return bad


def collect_safe_zone_receipts(jobs, base_dir):
    receipts = {}
    for job in jobs:
        margin = job.get("safe_zone")
        if margin is None:
            continue
        out = job["out"] if os.path.isabs(job["out"]) else os.path.join(base_dir, job["out"])
        label = str(job.get("label", job["out"]))
        receipts[label] = scene_safe_zone_receipt(out, float(margin))
    return receipts


def write_generation_receipt(base_dir, payload):
    path = os.path.join(base_dir, "_gen_result.json")
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def run_round(jobs, base_dir, cap, retry, effort, model, timeout=590):
    require_codex()  # ★ 전제조건 — 없으면 설치 안내 후 중단
    results = []
    with ThreadPoolExecutor(max_workers=cap) as ex:
        futs = {ex.submit(_run_one, j, base_dir, retry, i, effort, model, timeout): j.get("label", i)
                for i, j in enumerate(jobs)}
        for fut in as_completed(futs):
            r = fut.result()
            results.append(r)
            mark = "✓" if r["status"] == "OK" else ("!" if r["status"].startswith("WARN") else "✗")
            extra = f" {r.get('size_kb')}KB" if r.get("size_kb") else ""
            print(f"  {mark} {r['label']:20} {r['status']}{extra}", flush=True)
    return results


def _sweep(base_dir, keep=False):
    """생성이 끝난 .cxwork 격리 홈을 지운다.

    ★ 잡마다 시작 시 rmtree로 초기화하므로 재사용되지 않는 순수 중간 산물이다.
      정리하지 않으면 덱 하나당 수백 MB가 쌓인다(실측: 17개 폴더 9.1GB).
      --keep-work로 디버깅 시 보존할 수 있다.
    """
    if keep:
        return
    work = os.path.join(base_dir, ".cxwork")
    if not os.path.isdir(work):
        return
    n = sum(len(fs) for _, _, fs in os.walk(work))
    sz = 0
    for r, _, fs in os.walk(work):
        for f in fs:
            try:
                sz += os.path.getsize(os.path.join(r, f))
            except OSError:
                pass

    # codex가 .codexhome/.tmp/marketplace 캐시를 읽기 전용으로 만든다.
    # shutil.rmtree는 읽기 전용 파일에서 WinError 5로 실패한다(실측 292건).
    # onerror로 속성을 풀고 재시도해야 지워진다.
    import stat as _stat

    def _force(fn, path, exc):
        try:
            os.chmod(path, _stat.S_IWRITE)
            fn(path)
        except OSError:
            pass

    shutil.rmtree(work, onerror=_force)
    left = os.path.isdir(work)
    if sz:
        print("[정리] .cxwork %d파일 %.0fMB %s"
              % (n, sz / 1024 / 1024, "잔존(핸들 점유)" if left else "삭제"), flush=True)


def _hint(base_dir):
    """남은 .cxwork 용량을 알린다. 실제 삭제는 다음 실행 시작 시 이뤄진다."""
    work = os.path.join(base_dir, ".cxwork")
    if not os.path.isdir(work):
        return
    sz = 0
    for r, _, fs in os.walk(work):
        for f in fs:
            try:
                sz += os.path.getsize(os.path.join(r, f))
            except OSError:
                pass
    if sz > 50 * 1024 * 1024:
        print("[안내] .cxwork %.0fMB — 다음 생성 시 자동 정리됨 (즉시: rm -rf %s)"
              % (sz / 1024 / 1024, work), flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("jobs_json")
    ap.add_argument("--cap", type=int, default=0,
                    help="동시 실행 캡 (0=자동: min(잡수, 코어//2, 10). 격리홈이라 고병렬 안전)")
    ap.add_argument("--retry", type=int, default=1, help="잡별 재시도 (기본 1)")
    ap.add_argument("--loop", type=int, default=3, help="재귀 개선 라운드 상한 (기본 3) — 전부 통과 시 조기 종료")
    ap.add_argument("--effort", default=None, help="reasoning effort (low/medium/high/xhigh)")
    ap.add_argument("--model", default=None, help="codex 모델 (gpt-5.5 최강 / gpt-5.4 균형)")
    ap.add_argument("--timeout", type=int, default=590, help="잡당 codex 타임아웃(초)")
    ap.add_argument("--keep-work", action="store_true",
                    help=".cxwork 격리 홈을 남긴다 (디버깅용, 덱당 수백 MB)")
    ap.add_argument("--dup-check", action="store_true",
                    help="중복 헤드라인(오염) 검사 켜기 — 격리 없는 옛 파이프라인에서만. 에디토리얼 덱은 오탐 유발하니 OFF 권장")
    args = ap.parse_args()

    with open(args.jobs_json, encoding="utf-8") as f:
        all_jobs = json.load(f)
    base_dir = os.path.dirname(os.path.abspath(args.jobs_json))

    # 시작 시 한 번 — 이전 실행이 비정상 종료해 남긴 것을 회수한다.
    _sweep(base_dir, args.keep_work)

    if not args.cap:
        # 자동 동시성(2026-08-01 G002): 고정 5는 20코어 머신에서 과소.
        # 잡 수를 넘지 않고, 코어의 절반, 최대 10으로 제한.
        args.cap = max(1, min(len(all_jobs), (os.cpu_count() or 8) // 2, 10))
        print(f"[cap 자동] {args.cap} (잡 {len(all_jobs)}, 코어 {os.cpu_count()})", flush=True)

    # 선검증: 이미 정상인 슬라이드는 재생성하지 않음 (기존 결과 재활용)
    pre = verify(all_jobs, base_dir, args.dup_check)
    if not pre:
        print(f"[선검증] 전 {len(all_jobs)}장 이미 정상 — 생성 생략", flush=True)
        write_generation_receipt(
            base_dir,
            {
                "rounds": 0,
                "clean": True,
                "safeZones": collect_safe_zone_receipts(all_jobs, base_dir),
            },
        )
        return
    if pre and len(pre) < len(all_jobs):
        pending = [j for j in all_jobs if j.get("label") in pre]
        print(f"[선검증] 정상 {len(all_jobs)-len(pending)}장 유지, 불량 {len(pending)}장만 재생성 대상: "
              + ", ".join(f"{k}[{v}]" for k, v in pre.items()), flush=True)
    else:
        pending = all_jobs
    for rnd in range(1, args.loop + 1):
        print(f"[라운드 {rnd}/{args.loop}] {len(pending)}개 잡 · 동시성 {args.cap} · 재시도 {args.retry} · 격리홈 ON", flush=True)
        run_round(pending, base_dir, args.cap, args.retry, args.effort, args.model, args.timeout)
        bad = verify(all_jobs, base_dir, args.dup_check)
        if not bad:
            print(f"\n결과: 전 {len(all_jobs)}장 통과 (크기·중복 검증 clean) — 라운드 {rnd}에서 완료", flush=True)
            write_generation_receipt(
                base_dir,
                {
                    "rounds": rnd,
                    "clean": True,
                    "safeZones": collect_safe_zone_receipts(all_jobs, base_dir),
                },
            )
            _sweep(base_dir, args.keep_work)
            return
        print(f"  재생성 대상 {len(bad)}: " + ", ".join(f"{k}[{v}]" for k, v in bad.items()), flush=True)
        pending = [j for j in all_jobs if j.get("label") in bad]
    # 루프 소진
    bad = verify(all_jobs, base_dir)
    print(f"\n결과: 루프 {args.loop}회 소진, 잔여 {len(bad)}장: " + ", ".join(bad), flush=True)
    write_generation_receipt(
        base_dir,
        {"rounds": args.loop, "clean": False, "remaining": list(bad)},
    )
    _sweep(base_dir, args.keep_work)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
