# Odoo CRM - môi trường phát triển

Kho này gồm 2 phần:

| Thư mục | Nội dung | Ghi chú |
| --- | --- | --- |
| `odoo/` | Source Odoo 20.0 (nhánh `20.0`, git clone) | **Không sửa** |
| `custom-addons/` | Module riêng của công ty | Nơi làm việc |

- Database: PostgreSQL trong Docker `odoo-crm-db` (127.0.0.1:**15443**), DB `odoo-crm`
- Server: <http://localhost:8069> (`python odoo-bin -c odoo.conf`)
- Cấu hình: `odoo/odoo.conf` (đã thêm `custom-addons` vào `addons_path`)

## Module nghiệp vụ đã cài

| Module | Chức năng chính |
| --- | --- |
| `company_approval` | Phiếu phê duyệt nội bộ (mua hàng, thanh toán, nghỉ phép) |
| `company_sale_approval` | Duyệt chiết khấu vượt hạn mức, chặn bán dưới giá vốn |
| `company_logistics` | Duyệt chuyển kho nội bộ, cấu hình hãng vận chuyển, tạo vận đơn |
| `company_hr_payroll` | Phiếu lương từ chấm công, bảo hiểm, thuế TNCN, KPI |
| `company_einvoice` | Cấu hình và gửi hóa đơn điện tử VNPT/Viettel (có chế độ chạy thử) |
| `company_omnichannel` | Nhận webhook Zalo OA / Facebook / website, tạo lead CRM |
| `company_payment_approval` | Duyệt phiếu chi vượt hạn mức trước khi Confirm |

> Duyệt đơn mua hàng dùng cơ chế có sẵn của Odoo: **Purchase > Configuration >
> Settings > Levels of Approvals** (đã bật 2 bước, hạn mức 5.000). Xem hướng dẫn
> trong tài liệu module.

Xem chi tiết cách dùng và phần cần tài khoản thật:
[Module nghiệp vụ công ty](docs/custom-modules.md).

## Chạy nhanh

```powershell
cd odoo
python odoo-bin -c odoo.conf
```

Chế độ dev (tự nạp lại XML/QWeb, không cần tắt server khi sửa view):

```powershell
cd odoo
python odoo-bin -c odoo.conf --dev=qweb,xml
```

## Tài liệu

Đọc theo thứ tự này:

1. [Playbook phát triển module](docs/odoo-module-playbook.md) — **quyết định thiết kế**:
   chọn tầng can thiệp, điểm chặn, quyền, cấu hình, bẫy nghiệp vụ VN.
2. [Quy trình phát triển module](docs/odoo-dev-workflow.md) — **thao tác**: môi trường,
   vòng lặp dev, lỗi đặc thù Odoo 20, backup, deploy.
3. [Module nghiệp vụ đã cài](docs/custom-modules.md) — module nào đang chạy, dùng sao,
   phần nào cần tài khoản thật.

Module mẫu để copy cấu trúc: [`custom-addons/company_approval`](custom-addons/company_approval)

## Việc đầu tiên khi mở máy

```powershell
docker start odoo-crm-db
cd odoo
python odoo-bin -c odoo.conf
```
