# Custom addons

Mọi module do công ty tự phát triển đặt ở đây. Thư mục này đã được khai báo
trong `odoo/odoo.conf`:

```
addons_path = addons,D:\DATA E\BUIVANVU\2026\phanmem\odoo-crm\custom-addons
```

## Quy ước

- Mỗi module = một nghiệp vụ, tên `snake_case`, nên có prefix công ty
  (`company_`, `vn_`, ...).
- Không copy/sửa module trong `odoo/addons` (core). Muốn đổi core thì
  `_inherit` model và `xpath` view từ module ở đây.
- Mỗi module phải có:
  - `__manifest__.py` với `depends` đầy đủ
  - `security/ir.access.csv` (định dạng Odoo 20, xem module mẫu)
  - `views/`, `models/`, `tests/`
  - `i18n/vi.po` nếu có chuỗi hiển thị
- Đặt `version` dạng `20.0.x.y.z` để dễ đối chiếu khi nâng cấp Odoo.

## Module mẫu

`company_approval/` là template đầy đủ: model mới + sequence + workflow
duyệt + chatter + phân quyền + menu + test + bản dịch tiếng Việt.

Sao chép rồi đổi tên để bắt đầu module mới:

```powershell
Copy-Item -Recurse company_approval company_<nghiepvu>
# rồi sửa __manifest__.py, tên model, xml id, menu, security
```
