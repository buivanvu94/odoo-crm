# Module nghiệp vụ công ty (đã cài trên `odoo-crm`)

Tài liệu này mô tả 7 module trong `custom-addons/`, cách dùng, nơi cấu hình và
những phần **cần tài khoản/API thật** mới chạy được.

## Trạng thái

| Module | Phụ thuộc | Trạng thái | Test |
| --- | --- | --- | --- |
| `company_approval` | `mail` | Đã cài | 6 |
| `company_sale_approval` | `sale_management` | Đã cài | 4 |
| `company_logistics` | `stock_delivery` | Đã cài | 3 |
| `company_hr_payroll` | `hr_attendance` | Đã cài | 4 |
| `company_einvoice` | `account` | Đã cài | 2 |
| `company_omnichannel` | `crm` | Đã cài | 3 |
| `company_payment_approval` | `account` | Đã cài | 5 |

- Tổng: **27 test, 0 failed, 0 error** (`custom-tests.log`).
- Server dev: <http://localhost:8069>, DB `odoo-crm`.
- Log cài đặt: `custom-install.log`.

---

## 1. `company_approval` - Phê duyệt nội bộ

Phiếu yêu cầu/duyệt tổng quát cho mua hàng, thanh toán, nghỉ phép, khác.

**Dùng**

1. Menu **Approvals > Requests > New**.
2. Chọn loại, số tiền, lý do, người đề nghị.
3. **Submit** để gửi duyệt.
4. Quản lý vào **Approvals > Waiting Approval** để **Approve** hoặc **Refuse**.

**Phân quyền**

- `group_approval_user`: tạo phiếu; chỉ thấy phiếu do mình tạo.
- `group_approval_manager`: thấy tất cả, được duyệt/từ chối.

**Lưu ý:** đây là sổ phê duyệt độc lập, **không tự động** tạo/ghi sổ bút toán
mua hàng hay thanh toán. Muốn chặn trực tiếp trên đơn mua/phiếu chi thì cần
thêm logic vào `purchase.order` / `account.payment` (có thể làm tiếp).

---

## 2. `company_sale_approval` - Duyệt chiết khấu / giá bán

**Cấu hình:** **Sales > Configuration > Settings**

- `Giới hạn chiết khấu (%)`: mức chiết khấu tối đa mỗi dòng hàng nhân viên được
  tự quyết (mặc định 10%).
- `Chặn bán dưới giá vốn`: yêu cầu duyệt nếu đơn giá sau chiết khấu thấp hơn
  `standard_price` của sản phẩm.

**Luồng**

1. Tạo báo giá/đơn bán như bình thường.
2. Nếu vượt hạn mức hoặc dưới giá vốn, đơn tự đánh dấu **Cần duyệt giá**.
3. Nhấn **Request Price Approval**.
4. Quản lý vào **Sales > Orders > Duyệt giá bán** (hoặc mở đơn) để
   **Approve / Refuse**.
5. Chỉ sau khi **Approved** mới bấm **Confirm** được.

Sửa dòng hàng sau khi đã duyệt sẽ tự đưa trạng thái về **Chờ duyệt**.

**Phân quyền:** `group_sale_price_manager` (quản lý kinh doanh).

---

## 3. `company_logistics` - Duyệt chuyển kho & vận đơn

**Cấu hình:** **Inventory > Configuration > Settings**

- `Duyệt chuyển kho nội bộ`: bật/tắt.
- `Hạn mức chuyển kho tự động`: phiếu chuyển kho nội bộ có giá trị vượt mức
  phải được quản lý kho duyệt (mặc định 5.000).

**Duyệt phiếu kho**

1. Tạo **Internal Transfer**, thêm hàng.
2. Nếu vượt hạn mức, nút **Request Warehouse Approval** hiện ra.
3. Quản lý kho bấm **Approve Transfer** / **Refuse Transfer**.
4. Phiếu chưa duyệt sẽ bị chặn khi **Validate**.

**Vận đơn**

- Trên **Inventory > Configuration > Delivery > Carriers**, mỗi hãng có thêm:
  `Đơn vị vận chuyển VN` (GHN / Viettel Post / khác), `API Endpoint`,
  `API Token`, `Shop / Customer ID`.
- Trên phiếu kho có nút **Create Shipment**. Nếu carrier đã có endpoint/token,
  module gọi API, lưu request/response vào `company.shipment.log` và ghi
  `tracking_ref` lên phiếu.
- Xem lịch sử: **Inventory > Configuration > Lịch sử vận đơn**.

**Chưa chạy thật được:** cần endpoint + token + shop id do GHN/Viettel Post cấp.
Chưa có tài khoản thì chỉ xem được luồng duyệt kho và log lỗi/cấu hình.

---

## 4. `company_hr_payroll` - Lương từ chấm công & KPI

Odoo Community không có `hr_payroll`/`hr_contract`, nên module này tự tính phiếu
lương từ dữ liệu `hr.attendance`.

**Cấu hình nhân viên:** mở **Employees**, tab **Company Payroll**

- Lương cơ bản/tháng, phụ cấp/tháng, lương đóng bảo hiểm, số người phụ thuộc.

**Cấu hình công ty:** **Settings > Companies > (công ty) > tab Payroll**

- Ngày công chuẩn, hệ số làm thêm, tỷ lệ bảo hiểm NLĐ/NSDLĐ, mức trần bảo hiểm,
  giảm trừ bản thân, giảm trừ người phụ thuộc.

**Tạo phiếu lương**

1. **Employees > Bảng lương > Phiếu lương > New**.
2. Chọn nhân viên, tháng, năm.
3. Bấm **Compute** (tính ngày công, tăng ca, bảo hiểm, thuế TNCN, thực lĩnh).
4. **Confirm** rồi **Mark as Paid**.

Công thức mặc định:

- Bảo hiểm NLĐ: 10,5% (BHXH 8% + BHYT 1,5% + BHTN 1%).
- Bảo hiểm NSDLĐ: 21,5%.
- Thuế TNCN: biểu lũy tiến 7 bậc, giảm trừ bản thân/người phụ thuộc.

**KPI:** **Employees > KPI nhân viên**, nhập chỉ tiêu/thực tế theo nhân viên,
tháng, năm; module tính `score` và `passed`.

**Giới hạn:** chưa có hợp đồng lao động, bảng phụ cấp chi tiết, nghỉ phép, thưởng,
thanh toán lương qua ngân hàng. Đây là bản tính lương tối giản dựa trên chấm công.

---

## 5. `company_einvoice` - Hóa đơn điện tử VNPT / Viettel

**Cấu hình:** **Invoicing > Configuration > E-Invoice Providers**

- Nhà cung cấp: VNPT / Viettel / khác.
- `API Endpoint`, tài khoản/mật khẩu hoặc access token.
- Mẫu số, ký hiệu hóa đơn.
- `Chế độ chạy thử` (mặc định **bật**): chỉ tạo payload, không gọi API.

**Gửi hóa đơn**

1. Tạo hóa đơn khách hàng, **Post**.
2. Trên form hóa đơn, tab **E-Invoice**:
   - **Prepare E-Invoice**: tạo payload JSON và lưu lại.
   - **Send E-Invoice**: gọi nhà cung cấp (nếu tắt chạy thử), lưu response,
     số hóa đơn, trạng thái.
3. Xem `Payload` / `Response` ngay trên tab.

**Chưa chạy thật được:** payload hiện là JSON chung, **chưa phải schema chính
thức** của VNPT/Viettel. Muốn phát hành thật cần:

- Tài khoản API và endpoint do nhà cung cấp cấp.
- Mapping payload đúng tài liệu API của từng nhà cung cấp.
- Chữ ký số / token theo hợp đồng.

Core Odoo đã có `l10n_vn_edi_viettel` (đã cài) để tham khảo/ dùng song song.

---

## 6. `company_omnichannel` - Zalo OA / Facebook / Website → CRM

**Cấu hình:** **CRM > Configuration > Omnichannel**

Mỗi kênh khai báo:

- Kênh: Zalo OA / Facebook / Website.
- `Verify Token`, `App ID`, `App Secret`, `Page / OA ID`, `Access Token`.
- Team, nhân viên phụ trách, nguồn mặc định.
- Form hiển thị sẵn `Webhook URL` và `Verify URL` để dán vào nền tảng.

**Endpoint**

- Xác thực: `GET /company/omnichannel/verify/<config_id>?hub.verify_token=...&hub.challenge=...`
- Nhận sự kiện: `POST /company/omnichannel/webhook/<config_id>`

**Xử lý**

- Zalo OA: đọc `sender`, `message`.
- Facebook: đọc `entry[].changes[].value` (leadgen) hoặc `messaging`.
- Website: JSON `{name, phone, email, message}`.
- Mỗi payload được lưu vào **Tin nhắn omnichannel**; nếu hợp lệ thì tạo
  `crm.lead`, gắn team/nhân viên/nguồn.
- Facebook có `App Secret`: kiểm tra header `X-Hub-Signature-256`.

**Chưa chạy thật được:**

- Cần URL public HTTPS (dùng ngrok/cloudflared khi dev) và token/app secret thật.
- Module **chỉ nhận** sự kiện, chưa gửi tin nhắn trả lời lại Zalo/Facebook.
- Chưa chống trùng theo `external_id`: mỗi webhook tạo một lead mới.

---

## 7. `company_payment_approval` - Duyệt phiếu chi / thanh toán

**Cấu hình:** **Invoicing > Configuration > Settings > Payment Approval**

- `Bật duyệt thanh toán`: bật/tắt quy trình.
- `Hạn mức thanh toán tự động`: phiếu chi có giá trị (quy đổi về tiền tệ
  công ty) lớn hơn mức này phải được duyệt (mặc định 5.000).

**Luồng**

1. Tạo phiếu thanh toán chi ra (**Vendors > Payments > New**, chọn **Send**).
2. Nếu vượt hạn mức, phiếu tự đánh dấu **Cần duyệt thanh toán**.
3. Nhấn **Request Payment Approval**.
4. Quản lý kế toán vào **Invoicing > Vendors > Duyệt thanh toán** (hoặc mở
   phiếu) để **Approve Payment** / **Refuse Payment**.
5. Chỉ sau khi **Approved** mới bấm **Confirm** được.

Sửa số tiền, đối tác, nhật ký hoặc loại thanh toán sau khi duyệt sẽ tự đưa về
**Chờ duyệt**. Phiếu thu (inbound) không bị chặn.

**Phân quyền:** `group_payment_approval_manager` (quản lý kế toán).

**Lưu ý:** chỉ chặn thao tác **Confirm** trên phiếu thanh toán. Nếu công ty
muốn duyệt cả hóa đơn nhà cung cấp trước khi ghi sổ, cần mở rộng thêm trên
`account.move` (chưa nằm trong module này).

---

## Duyệt đơn mua hàng (có sẵn trong Odoo core)

Không cần module riêng: Odoo 20 đã có cơ chế duyệt 2 bước cho đơn mua.

**Đã bật sẵn** trên công ty hiện tại:

- **Levels of Approvals** = *Get 2 levels of approvals to confirm a purchase
  order*.
- **Double validation amount** = 5.000 (theo tiền tệ công ty).

Cách kiểm tra / đổi lại:

1. Vào **Purchase > Configuration > Settings**.
2. Chọn **Levels of Approvals** = *Get 2 levels of approvals to confirm a
   purchase order*.
3. Đặt **Double validation amount**.
4. Đơn mua vượt mức sẽ chuyển trạng thái **To Approve**; quản lý mua hàng bấm
   **Approve** rồi mới **Confirm**.

---

## Cài đặt / nâng cấp / test

```powershell
cd odoo

# Cài tất cả module (server phải tắt)
python odoo-bin -c odoo.conf -d odoo-crm -i company_approval,company_sale_approval,company_logistics,company_hr_payroll,company_einvoice,company_omnichannel,company_payment_approval --stop-after-init

# Nâng cấp sau khi sửa code/XML
python odoo-bin -c odoo.conf -d odoo-crm -u company_sale_approval --stop-after-init

# Test
python odoo-bin -c odoo.conf -d odoo-crm -u company_sale_approval --test-tags /company_sale_approval --stop-after-init
```

Khi chạy test trên Windows, nếu gặp lỗi filestore `.__gc`, xem mục
[Lỗi thường gặp](odoo-dev-workflow.md#11-lỗi-thường-gặp).

---

## Việc cần làm để chạy production

1. Đổi mật khẩu admin, tắt `list_db`, bật HTTPS.
2. Cấu hình backup DB + filestore tự động.
3. Điền tài khoản thật: GHN/Viettel Post, VNPT/Viettel, Zalo OA, Facebook App.
4. Kiểm tra lại hạn mức duyệt và biểu thuế/bảo hiểm với kế toán.
5. Chạy `-u` trên bản copy DB trước khi lên production.
