# Playbook phát triển module Odoo

Tài liệu này chốt **cách ra quyết định** khi làm một module Odoo: can thiệp ở tầng
nào, chặn ở điểm nào, dữ liệu thuộc object nào, và cái gì phải cấu hình thay vì
viết code.

Đọc cùng:

- Cách chạy lệnh, môi trường, lỗi cú pháp Odoo 20 → [Quy trình phát triển module](odoo-dev-workflow.md)
- Module đã cài và cách dùng → [Module nghiệp vụ công ty](custom-modules.md)

Ranh giới: file này sở hữu **quyết định (WHY)**. File workflow sở hữu **thao tác
(HOW)**. Không chép lệnh hay đoạn code sang đây.

---

## 1. Nguyên tắc 0 — Odoo đã có thì đừng viết lại

Odoo là ERP đóng gói. Phần lớn yêu cầu của một công ty Việt Nam **đã tồn tại**
trong core hoặc `l10n_vn`, chỉ là nằm ở tầng khác chứ không phải một module có
tên đúng như mình tưởng.

Ba câu hỏi bắt buộc, theo thứ tự, trước khi viết dòng code nào:

1. **Core đã có chưa?** → đọc source trong `odoo/addons/`, không đoán.
2. **Có module OCA / community làm rồi chưa?**
3. **Có bật bằng cấu hình được không?**

Chỉ khi cả ba đều "không" mới được tạo module mới.

### Bằng chứng trong repo này

Cùng một chữ **"phê duyệt"**, ba cách xử lý khác nhau hoàn toàn:

| Yêu cầu | Cách đúng | Chi phí |
| --- | --- | --- |
| Duyệt đơn mua hàng vượt hạn mức | Bật cơ chế có sẵn của core: **Purchase › Configuration › Settings › Levels of Approvals** (field `po_double_validation` trong `odoo/addons/purchase/models/res_company.py`; hạn mức tính theo tiền tệ công ty). Không viết module. | 0 dòng code |
| Duyệt chiết khấu / bán dưới giá vốn trên báo giá | `company_sale_approval` — core không có | 1 module |
| Duyệt phiếu chi trước khi Confirm | `company_payment_approval` — core không có | 1 module |

Người làm theo đặc tả thuần sẽ viết 3 module. Người hiểu Odoo viết 2 module +
1 lần bật cấu hình. Đó là toàn bộ khác biệt giữa một dự án Odoo sống được và một
dự án phải viết lại sau 2 năm.

> Hệ quả: **không bao giờ** tạo module chỉ để "làm đúng quy trình công ty" khi
> core đã có sẵn một cơ chế tương đương. Sửa ngưỡng, bật tính năng, đổi tên nhãn
> là đủ.

---

## 2. Thang can thiệp — luôn đi từ trên xuống

Chỉ xuống tầng dưới khi tầng trên không giải quyết được.

| # | Tầng | Dấu hiệu chọn tầng này | Ví dụ trong repo |
| --- | --- | --- | --- |
| 1 | **Cấu hình** | Core có tính năng, chỉ thiếu bật/đổi ngưỡng | Duyệt đơn mua 2 bước |
| 2 | **Dữ liệu** | Core có cơ chế, chỉ thiếu bản ghi | Sequence, pricelist, route kho, nhóm quyền |
| 3 | **Kế thừa model** (`_inherit`) | Cần thêm field hoặc thêm một điều kiện chặn trên object có sẵn | `company_sale_approval/models/sale_order.py` |
| 4 | **Kế thừa view** (`inherit_id` + xpath) | Chỉ đổi giao diện, không đổi dữ liệu | — |
| 5 | **Model mới** (`_name`) | Nghiệp vụ chưa có object nào chứa được | `company.approval.request`, `company.payslip`, `company.channel.config` |
| 6 | **Tích hợp ngoài** (API/webhook) | Phải nói chuyện với hệ thống khác | `company_einvoice`, `company_omnichannel` |
| — | ~~Sửa `odoo/addons`~~ | **Không bao giờ** | Mất toàn bộ khi nâng cấp |

Cách các module hiện tại đang phân tầng — dùng làm mẫu:

- **Cấu hình trên `res.company`, mở ra bằng `res.config.settings`**:
  `company_sale_approval`, `company_payment_approval`, `company_logistics`,
  `company_hr_payroll`.
- **Logic chèn vào object giao dịch có sẵn**: `sale.order`, `account.payment`,
  `stock.picking`, `account.move`.
- **Model mới chỉ khi thật sự có khái niệm mới**: phiếu đề nghị, phiếu lương,
  KPI, log vận đơn, cấu hình kênh, log tin nhắn.

Nếu một yêu cầu buộc bạn tạo model mới nhưng dữ liệu thực chất là "một đơn mua
hàng có thêm bước duyệt", bạn đang chọn sai tầng.

---

## 3. Ánh xạ yêu cầu → object Odoo

Đây là kỹ năng quan trọng nhất khi làm Odoo, và là chỗ BA thường chỉ mô tả quy
trình mà quên trả lời.

| Nghiệp vụ | Object gốc | Điểm can thiệp |
| --- | --- | --- |
| Đề nghị mua hàng nội bộ | `purchase.order` | `button_confirm`, state `to approve` |
| Duyệt chiết khấu báo giá | `sale.order` | `action_confirm` + `write` reset duyệt |
| Duyệt phiếu chi | `account.payment` | `action_post` |
| Duyệt chuyển kho nội bộ | `stock.picking` | `button_validate` |
| Xuất hóa đơn điện tử | `account.move` | nút riêng + `account.move` fields |
| Vận đơn / tracking | `stock.picking` + `delivery.carrier` | `action_book_shipment` |
| Lead từ Zalo / Facebook / website | `crm.lead` | controller webhook → `crm.lead` |
| Chấm công | `hr.attendance` | đọc, không sửa |
| Lương | `hr.employee` (lương tháng) + `hr.attendance` | model phiếu lương riêng `company.payslip` |
| KPI nhân viên | model riêng | `company.kpi` |
| Phiếu đề nghị tổng hợp | model riêng | `company.approval.request` |

Quy tắc: nếu dữ liệu **đã là** một đơn hàng / hóa đơn / phiếu kho, thì đừng tạo
object song song. Tạo object song song = hai nguồn sự thật = số liệu lệch.

---

## 4. Năm quyết định phải chốt trước khi code

**BA cho Odoo là bài toán ánh xạ, không phải bài toán mô tả.** BA thường hỏi
"quy trình công ty đang chạy thế nào?" rồi vẽ flowchart nhiều bước. Bản đặc tả
đó cần, nhưng chưa đủ để ra một module Odoo tốt: mỗi bước trong flowchart phải
được ánh xạ về object, điểm chặn, quyền và dữ liệu báo cáo dưới đây.

Thiếu một câu là có nguy cơ phải làm lại từ đầu.

### 4.1. Dữ liệu thuộc object nào?

Model là schema database. Đổi model sau khi đã có dữ liệu thật = viết migration.
Chọn sai ở bước này là loại lỗi đắt nhất trong Odoo.

### 4.2. Chặn ở điểm nào?

Ẩn nút trên view **không phải** là chặn. Người dùng vẫn gọi được qua RPC/API hoặc
qua một luồng khác. Luôn chặn trong method Python của object, trước `super()`.

Điểm chặn chuẩn theo từng object (xem bảng §3). Điểm chặn sai thường gặp:

- Chặn ở `create` khi nghiệp vụ chặn ở bước xác nhận → user tạo nháp thoải mái,
  nhưng xác nhận thì lọt.
- Chặn ở view khi có import Excel / API → lọt sạch.
- Chặn ở `action_confirm` nhưng không chặn `button_confirm` của bản ghi con.

### 4.3. Ai được làm gì?

Odoo mặc định **deny all**: model mới mà không khai báo `ir.access` thì không ai
mở được, kể cả admin.

Phải đúng cả hai lớp:

- **Model-level**: `security/ir.access.csv`.
- **Record-level**: cùng file, dòng **không có group** + `domain`
  (Odoo 20 gộp `ir.rule` vào đây).

Và phải kiểm tra lại trong Python bằng `has_group` cho các hành động nhạy cảm —
xem cách áp dụng trong
`company_approval/models/company_approval_request.py`.

### 4.4. Sửa sau khi đã duyệt thì sao?

Đây là lỗ hổng kinh điển và là câu BA thường bỏ qua:

> Duyệt xong → sửa giá / sửa số tiền / thêm dòng → phiếu đã duyệt trở nên vô
> nghĩa, nhưng hệ thống vẫn coi là đã duyệt.

Bắt buộc có invariant: **dữ liệu nghiệp vụ thay đổi thì trạng thái duyệt phải
quay về chưa duyệt**. Cách làm đã dùng trong repo: override `write()` trên
`sale.order` và `account.payment` để reset khi các trường liên quan thay đổi.

Khi thiết kế, hỏi thêm: duyệt xong có được hủy không? Hủy xong có được duyệt lại
không? Ai được hủy?

### 4.5. Báo cáo lấy số từ đâu?

Nếu nghiệp vụ cần báo cáo (ai duyệt, duyệt khi nào, bao nhiêu phiếu bị từ chối,
thời gian chờ duyệt…), các con số đó phải là **field lưu sẵn** ngay từ thiết kế
đầu tiên. Thiếu field thì sau này chỉ còn cách đọc ngược chatter — không lọc,
không group, không pivot được.

Tối thiểu cho mọi luồng duyệt: trạng thái duyệt, người duyệt, thời điểm duyệt,
ghi chú. Mẫu trong repo: `approver_id` / `date_approval` ở
`company_approval/models/company_approval_request.py`; nhóm field
`price_approval_*` ở `company_sale_approval/models/sale_order.py` và
`payment_approval_*` ở `company_payment_approval/models/account_payment.py`.
Khi reset duyệt (§4.4) phải xóa cả các field này, không chỉ đổi trạng thái.

---

## 5. Cấu hình thay vì hardcode

Mọi con số nghiệp vụ đều sẽ thay đổi. Đưa lên `res.company`, mở ra bằng
`res.config.settings`, đặt default hợp lý.

Đã áp dụng cho: hạn mức duyệt chiết khấu, hạn mức duyệt phiếu chi, hạn mức duyệt
chuyển kho, tỷ lệ bảo hiểm, mức giảm trừ gia cảnh, trần đóng bảo hiểm.

Quy tắc:

- **Ngưỡng tiền, %, tỷ lệ, thời hạn** → field cấu hình, không viết trong `if`.
- **Danh mục** (nhà cung cấp hóa đơn, hãng vận chuyển, kênh) → model cấu hình,
  không phải `Selection` cứng.
- **Biểu thuế / biểu phí** là dữ liệu, không phải code. Nếu buộc phải hardcode
  (ví dụ biểu thuế TNCN trong `company_hr_payroll/models/company_payslip.py`,
  hàm `_bracket_pit`) thì phải ghi rõ trong tài liệu module rằng **luật đổi là
  phải sửa code**, và ghi nguồn của biểu đó.
- **Default phải đúng đơn vị tiền tệ của công ty.** Một hạn mức `5000` là 5000
  USD hay 5000 VND — sai đơn vị là sai 25.000 lần. Luôn ghi đơn vị vào `string`
  hoặc `help` của field.

---

## 6. Bẫy nghiệp vụ Việt Nam

| Bẫy | Cách xử lý |
| --- | --- |
| Tiền tệ | Công ty mặc định USD; mọi hạn mức phải ghi rõ đơn vị. Đổi sang VND thì phải rà lại toàn bộ ngưỡng. |
| Thuế TNCN / bảo hiểm | Luật đổi theo năm. Tỷ lệ để ở `res.company`, biểu thuế phải có ghi chú chỗ sửa. |
| Hóa đơn điện tử | Payload thật của VNPT/Viettel khác "spec chung". Không hứa chạy được khi chưa có tài khoản thật; luôn có chế độ chạy thử. |
| Zalo / Facebook | Cần URL public HTTPS + verify token + app secret. Không test được bằng localhost. |
| Đa công ty | Mọi model nghiệp vụ phải có `company_id` + dòng `ir.access` giới hạn theo `company_ids`. |
| Chữ ký số | Là tích hợp ngoài, không phải field. Đừng giả lập bằng checkbox. |

---

## 7. Tích hợp hệ thống ngoài — 6 quy tắc

1. **Credential nằm trong cấu hình**, không nằm trong code, không commit.
2. **Dry-run là mặc định.** Chưa có tài khoản thật thì chỉ được tạo payload và
   ghi log, không được giả vờ đã gửi.
3. **Lưu request + response** vào bản ghi để đối soát (đã làm ở hóa đơn điện tử
   và log vận đơn).
4. **Idempotency**: mỗi payload cần khóa ngoài (`external_id`, `leadgen_id`,
   `message_id`) để không tạo trùng khi nhà cung cấp retry.
5. **Không chặn transaction của người dùng bằng lời gọi mạng dài.** Timeout, lỗi
   mạng, retry phải có đường thoát và có log.
6. **Không tuyên bố "đã tích hợp xong"** khi chưa có credential. Trạng thái đúng
   là: connector xong, chờ tài khoản.

---

## 8. Quy trình 6 bước khi nhận một yêu cầu mới

1. **Đọc core trước.** Tìm object, field, workflow có sẵn. Ghi lại đã tìm ở đâu.
2. **Chốt tầng can thiệp** theo §2. Nếu là tầng 1–2 thì dừng, không tạo module.
3. **Chốt 5 quyết định** theo §4 (object, điểm chặn, quyền, reset sau khi duyệt,
   field phục vụ báo cáo).
4. **Viết nhỏ nhất có thể**: field + cấu hình + điểm chặn + view + menu + i18n.
5. **Test 4 loại**: luồng chính, luồng bị chặn, phân quyền, và "sửa sau khi
   duyệt". Xem mẫu trong `custom-addons/company_approval/tests/`.
6. **Bàn giao**: chạy `-u` trên bản copy DB, cập nhật `docs/custom-modules.md`,
   rồi mới deploy theo workflow §10.

---

## 9. Gate A — checklist trước khi viết dòng code đầu tiên

- [ ] Đã đọc source core liên quan và ghi rõ core **không** làm được gì
- [ ] Đã loại trừ khả năng chỉ cần cấu hình
- [ ] Đã xác định object gốc và lý do không dùng object có sẵn (nếu tạo model mới)
- [ ] Đã xác định **điểm chặn** trong Python, không phải ẩn nút
- [ ] Đã xác định nhóm quyền: ai tạo, ai duyệt, ai xem
- [ ] Đã trả lời: sửa sau khi duyệt thì xử lý thế nào
- [ ] Đã liệt kê field cần cho báo cáo (người duyệt, ngày duyệt, trạng thái…)
- [ ] Đã liệt kê mọi con số sẽ thành cấu hình + đơn vị tiền tệ
- [ ] Đã xác định phần nào cần credential ngoài và phần nào chỉ dry-run

Gate B (kỹ thuật, trước khi báo xong) nằm ở mục **12. Checklist module trước
khi bàn giao** trong [Quy trình phát triển module](odoo-dev-workflow.md) — không
lặp lại ở đây.

---

## 10. Chống chỉ định

| Không làm | Vì sao |
| --- | --- |
| Sửa file trong `odoo/addons` | Mất khi `git pull` hoặc nâng cấp |
| Copy nguyên view/model core rồi sửa | Vỡ khi core đổi; dùng `inherit_id` + xpath |
| Tạo module mới cho việc core đã có | Hai nguồn sự thật, không nâng cấp được |
| Custom nhiều hơn mức cần | Mỗi dòng custom là một khoản nợ khi nâng cấp phiên bản Odoo; custom dày đến mức không nâng cấp được thì hệ thống chết dần |
| Module không có test | Sửa A vỡ B mà không ai biết cho đến khi lên production |
| Thiếu `i18n/vi.po` | Người dùng Việt mở ra thấy tiếng Anh và bỏ không dùng |
| Ẩn nút thay vì chặn quyền | Lách được qua RPC/import |
| Hardcode ngưỡng tiền / % / thuế | Nghiệp vụ đổi là phải deploy lại |
| Model nghiệp vụ không có `company_id` | Sai số liệu khi bật đa công ty |
| Báo "xong" khi chưa có test và chưa `-u` thử | Lỗi chỉ lộ trên production |
| Hứa tích hợp chạy được khi chưa có tài khoản | Không kiểm chứng được |
