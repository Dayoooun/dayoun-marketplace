# 견적서 모듈

## 입력 스키마

- `style`: `clean`, `office`, `brand`
- `title`: 문서 제목
- `supplier`: `company`, `representative`, `business_number`, `address`, `phone`, `logo_path`, `seal_path`
- `customer`: `company`, `contact`
- `vat_mode`: `exclusive` 또는 `inclusive`
- `items`: `name`, `spec`, `qty`, `unit_price`를 가진 배열
- `notes`: 특기사항 배열

`vat_mode: exclusive`이면 항목 합계를 공급가액으로 보고 부가세를 더합니다. `inclusive`이면 항목 합계를 총액으로 보고 공급가액을 역산하며, 그 사실을 특기사항에 자동으로 남깁니다. 빈 `spec`은 `-`로 표시합니다.

상호·대표자·사업자등록번호·주소·연락처는 만들지 않습니다. 사용자가 주지 않은 필드는 `[상호 입력]` 같은 placeholder로 둡니다. 견적번호는 사용자가 요청하고 값을 제공한 경우에만 입력 데이터로 확장합니다. 로고와 인장은 사용자 파일 경로만 받고, 없으면 상호와 `(인)`을 표시합니다.

합계와 한글 금액은 `quote_render.py`가 계산합니다. 반올림과 역산을 답변에서 직접 계산하지 않습니다. 인사말이나 이모지를 추가하지 않습니다.
