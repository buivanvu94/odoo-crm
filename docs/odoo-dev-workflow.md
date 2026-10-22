# Quy trình phát triển module riêng trên Odoo 20

Tài liệu này mô tả cách thêm nghiệp vụ riêng của công ty vào Odoo mà **không
sửa source core**, đúng với cách Odoo được thiết kế để mở rộng.

> Đây là tài liệu **thao tác**. Trước khi viết code, đọc
> [Playbook phát triển module](odoo-module-playbook.md) để chốt: core đã có chưa,
> can thiệp ở tầng nào, chặn ở điểm nào, quyền ra sao.

---

## 1. Môi trường hiện tại

| Thành phần | Giá trị |
| --- | --- |
| Odoo | 20.0 (`version_info = 20.0.0 final`) |
| Source core | `odoo/` - git nhánh `20.0` |
| Code công ty | `custom-addons/` (đã nằm trong `addons_path`) |
| PostgreSQL | Docker `odoo-crm-db`, `127.0.0.1:15443`, user/pass `odoo/odoo` |
| Database dev | `odoo-crm` |
| Web | <http://localhost:8069> |
| Python | 3.12.8 (đã cài requirements của Odoo) |
| Cấu hình | `odoo/odoo.conf` |

Kiểm tra:

```powershell
docker ps --filter name=odoo-crm-db
cd odoo
python odoo-bin --version
```

> Server đang chạy phải được **khởi động lại** thì mới thấy `custom-addons`
> trong `addons_path` và module mới.

---

## 2. Nguyên tắc: không sửa core

Odoo chia code thành:

- `odoo/addons/*`: module chuẩn (base, crm, sale, account, project...).
- `custom-addons/*`: module của công ty.

Nếu sửa trực tiếp file trong `odoo/addons`:

- `git pull` bản mới sẽ conflict hoặc mất code.
- Nâng cấp Odoo sẽ mất toàn bộ tùy chỉnh.
- Không review/trace được thay đổi của công ty.

Cách đúng để đổi hành vi core là **kế thừa**:

- Thêm field/business logic: model `_inherit`.
- Thêm/sửa giao diện: view `inherit_id` + `xpath`.
- Thêm menu/action/report: khai báo mới trong module của mình.
- Thay đổi quyền: thêm bản ghi `ir.access`, không sửa CSV core.

---

## 3. Một module Odoo gồm những gì

```
custom-addons/company_approval/
├── __manifest__.py              # khai báo module (bắt buộc)
├── __init__.py                  # import package Python
├── models/
│   ├── __init__.py
│   └── company_approval_request.py
├── security/
│   ├── company_approval_security.xml   # group, privilege
│   └── ir.access.csv                   # quyền truy cập (Odoo 20)
├── data/
│   └── ir_sequence_data.xml            # dữ liệu cấu hình (sequence)
├── views/
│   ├── company_approval_request_views.xml
│   └── company_approval_menus.xml
├── tests/
│   ├── __init__.py
│   └── test_company_approval.py
└── i18n/
    └── vi.po                           # bản dịch tiếng Việt
```

`__manifest__.py` khai báo:

```python
{
    'name': 'Company Approval',
    'version': '20.0.1.0.0',
    'depends': ['mail'],          # chỉ module dùng trực tiếp
    'data': [                     # thứ tự nạp quan trọng
        'security/company_approval_security.xml',
        'security/ir.access.csv',
        'data/ir_sequence_data.xml',
        'views/company_approval_request_views.xml',
        'views/company_approval_menus.xml',
    ],
    'application': True,
}
```

Thứ tự nạp: group/security trước, rồi data, rồi view/action/menu.

---

## 4. Vòng lặp phát triển hằng ngày

### Bước 0 - Dừng server đang chạy

`Ctrl+C` ở terminal đang chạy `python odoo-bin -c odoo.conf`.

Nếu muốn chạy song song bản dev, dùng cổng khác:

```powershell
python odoo-bin -c odoo.conf --http-port=8070
```

### Bước 1 - Tạo module mới

```powershell
cd odoo
python odoo-bin scaffold company_x ../custom-addons
```

> Scaffold của Odoo 20 vẫn sinh `security/ir.model.access.csv` kiểu cũ và
> `models/models.py` rỗng. Phải đổi sang `security/ir.access.csv` và tách file
> theo model. Xem module mẫu `company_approval` để copy cấu trúc đúng.

### Bước 2 - Cài module

```powershell
cd odoo
python odoo-bin -c odoo.conf -d odoo-crm -i company_x --stop-after-init
```

Hoặc bật server rồi vào **Settings > Apps > Update Apps List**, tìm module và
bấm **Activate**.

Kiểm tra log: không có `ERROR`, dòng `Module company_x loaded`.

### Bước 3 - Chỉ sửa XML/view/asset

Dùng dev mode để Odoo tự nạp lại khi lưu file:

```powershell
python odoo-bin -c odoo.conf --dev=qweb,xml
```

Hoặc nếu server đang chạy không có dev mode, nâng cấp module:

```powershell
python odoo-bin -c odoo.conf -d odoo-crm -u company_x --stop-after-init
```

### Bước 4 - Sửa Python (model, field, logic)

Bắt buộc **khởi động lại** server (hoặc cài `watchdog` rồi dùng `--dev=all`):

```powershell
pip install watchdog
python odoo-bin -c odoo.conf --dev=all
```

Khi **thêm/sửa field, model, XML data**: phải `-u company_x`.
Chỉ sửa thân hàm Python (logic) thì restart là đủ.

### Bước 5 - Chạy test

```powershell
cd odoo
python odoo-bin -c odoo.conf -d odoo-crm -u company_x `
  --test-tags /company_x --stop-after-init
```

Kết quả cuối log: `0 failed, 0 error(s) of N tests`.

### Bước 6 - Commit

Git repo nằm ở thư mục gốc dự án (gồm `custom-addons/`, `docs/`, `scripts/`).
`odoo/` là git clone riêng của core nên bị loại trong `.gitignore`, cùng với
`backups/`, log và file `*.conf` chứa mật khẩu — không commit lẫn vào nhau.

```powershell
git add custom-addons/company_approval docs
git commit -m "feat(approval): add internal approval workflow"
```

---

## 5. Phân quyền trên Odoo 20 (khác bản cũ)

Odoo 20 gộp `ir.model.access` và `ir.rule` thành **`ir.access`**. File chuẩn là
`security/ir.access.csv`, **không phải** `ir.model.access.csv`.

Cột:

```csv
id,name,model_id,group_id/id,operation,domain
```

- `operation`: tập con của `crud` (`r`, `cru`, `crud`...).
- Dòng **có group** = cấp quyền (OR giữa các group).
- Dòng **không có group** = giới hạn AND cho mọi user (dùng cho multi-company).
- Model không có dòng nào = **không ai truy cập được** (default deny).

Ví dụ thực tế trong module mẫu:

```csv
access_company_approval_request_user,company.approval.request.user,company.approval.request,company_approval.group_approval_user,cru,"[('requested_by', '=', user.id)]"
access_company_approval_request_manager,company.approval.request.manager,company.approval.request,company_approval.group_approval_manager,crud,
company_approval_request_company_rule,company.approval.request.company,company.approval.request,,crud,"[('company_id', 'in', company_ids)]"
```

- Nhân viên: chỉ thấy phiếu của mình.
- Người duyệt: toàn quyền.
- Mọi user (kể cả admin) bị giới hạn theo công ty đang chọn.

Group khai báo trong `security/*_security.xml`. Odoo 20 dùng
`res.groups.privilege` thay cho `category_id` cũ:

```xml
<record id="res_groups_privilege_company_approval" model="res.groups.privilege">
    <field name="name">Approvals</field>
    <field name="category_id" ref="base.module_category_productivity"/>
</record>

<record id="group_approval_user" model="res.groups">
    <field name="name">User</field>
    <field name="privilege_id" ref="res_groups_privilege_company_approval"/>
    <field name="implied_ids" eval="[(4, ref('base.group_user'))]"/>
</record>
```

> Chỉ ẩn nút trên giao diện **không đủ**. Luôn kiểm tra quyền trong method
> Python (xem `action_approve` trong module mẫu).

---

## 6. Mở rộng model/view có sẵn

Đây là việc phổ biến nhất: thêm field vào CRM lead, sale order, project task...

### 6.1 Thêm field

`models/crm_lead.py`:

```python
from odoo import fields, models


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    company_code = fields.Char(string='Company Code', tracking=True)
```

`models/__init__.py`:

```python
from . import crm_lead
```

### 6.2 Thêm field lên form

`views/crm_lead_views.xml`:

```xml
<record id="view_crm_lead_form_company_code" model="ir.ui.view">
    <field name="name">crm.lead.form.company.code</field>
    <field name="model">crm.lead</field>
    <field name="inherit_id" ref="crm.crm_lead_view_form"/>
    <field name="arch" type="xml">
        <xpath expr="//field[@name='partner_name']" position="after">
            <field name="company_code"/>
        </xpath>
    </field>
</record>
```

Quy tắc:

- `inherit_id` là XML id của view gốc.
- `xpath` neo theo **thuộc tính** (`@name`), không theo vị trí phần tử.
- Các `position`: `before`, `after`, `inside`, `replace`, `attributes`.
- Không copy toàn bộ view gốc rồi sửa.

### 6.3 Thêm menu vào menu có sẵn

```xml
<menuitem id="menu_company_approval_config"
          name="Approvals"
          parent="base.menu_custom"
          sequence="50"/>
```

(`base.menu_custom` là menu Settings > Technical / Custom.)

---

## 7. Test

Test nằm trong `tests/test_*.py`, được import từ `tests/__init__.py`.
Dùng `TransactionCase`, tag `post_install`.

Module mẫu có 6 test: tạo phiếu, gửi duyệt, duyệt, từ chối, chặn nhân viên
duyệt, chặn đọc phiếu người khác.

```powershell
cd odoo
python odoo-bin -c odoo.conf -d odoo-crm -u company_approval `
  --test-tags /company_approval --stop-after-init
```

---

## 8. Đa ngôn ngữ

- Chuỗi trong code/XML viết **tiếng Anh** (chuẩn Odoo).
- Bản dịch đặt ở `i18n/vi.po`.
- Odoo 20 dùng CLI `i18n` mới:

```powershell
cd odoo

# Xuất chuỗi cần dịch (ra stdout)
python odoo-bin i18n export company_approval -c odoo.conf -d odoo-crm -l vi -o -

# Nạp bản dịch vào DB
python odoo-bin i18n import -l vi ..\custom-addons\company_approval\i18n\vi.po `
  -c odoo.conf -d odoo-crm -w
```

Khi cài module mới, nếu tiếng Việt đã active, Odoo tự nạp `i18n/vi.po`.

---

## 9. Backup, restore, nhân bản DB

### Backup

```powershell
docker exec odoo-crm-db pg_dump -U odoo -Fc odoo-crm > backups\odoo-crm.dump
```

Nên backup **trước mỗi lần `-u`** module có thay đổi model/field.

### Restore

Dừng server trước, sau đó:

```powershell
docker exec odoo-crm-db dropdb -U odoo --if-exists odoo-crm
docker exec odoo-crm-db createdb -U odoo odoo-crm
docker exec -i odoo-crm-db pg_restore -U odoo -d odoo-crm < backups\odoo-crm.dump
```

### Nhân bản DB dev để thử nghiệm

```powershell
docker exec odoo-crm-db createdb -U odoo -T odoo-crm odoo-crm-test
```

Sau đó chạy server với `-d odoo-crm-test` và cổng khác.

---

## 10. Đưa lên production

1. Backup DB và filestore.
2. Copy `custom-addons/<module>` lên server production.
3. Cập nhật `addons_path` trong config production.
4. Chạy nâng cấp (server production đang tắt):

   ```bash
   python odoo-bin -c /etc/odoo/odoo.conf -d <db> -u <module> --stop-after-init
   ```

5. Khởi động lại service, kiểm tra log + smoke test.
6. **Không** bật `--dev` trên production.

Với thay đổi lớn: thử trên bản copy DB trước, đo thời gian `-u`, rồi mới làm
trên production.

---

## 11. Lỗi thường gặp

| Hiện tượng | Nguyên nhân / cách sửa |
| --- | --- |
| Module không hiện trong Apps | Sai `addons_path`, chưa restart, chưa **Update Apps List** |
| `no such directory ... skipped` | Đường dẫn trong `addons_path` sai hoặc có dấu cách không đúng |
| Sửa XML không có tác dụng | Chưa `-u module`, hoặc không bật `--dev=xml,qweb` |
| Sửa Python không có tác dụng | Chưa restart (trừ khi bật `--dev=all` + watchdog) |
| `AccessError` khi mở model mới | Thiếu dòng trong `security/ir.access.csv` (default deny) |
| Lỗi `xpath` khi nâng cấp | Neo theo vị trí hoặc theo field không còn tồn tại; dùng `@name` |
| View lỗi sau khi copy code mẫu | Odoo 20 dùng `<list>`, không dùng `<tree>`; `attrs` đã bỏ, dùng `invisible="..."` |
| `ir.model.access.csv` không có tác dụng | Odoo 20 dùng `ir.access.csv` (cột `operation`, `domain`) |
| Search view báo `Invalid attribute string/expand for element group` | Odoo 20 không cho `<group string="..." expand="0">` trong `<search>`; dùng `<group>` trơn |
| `ValueError: Invalid field 'name' in 'stock.move'` | Odoo 20 bỏ `name`/`product_uom` trên `stock.move`; dùng `product_id`, `uom_id`, `product_uom_qty` |
| `AssertionError ... __gc` khi chạy test | Filestore còn file GC dở dang. Xóa/khôi phục các file `*.__gc` trong `filestore\odoo-crm` (xem bên dưới) |
| Cổng 8069 bận | Đã có server chạy; dùng `--http-port=8070` |

### Dọn filestore `.__gc` trên Windows

Khi test bị `AssertionError` tại `ir_attachment._full_path` với file `*.__gc`:

```powershell
$root = "$env:LOCALAPPDATA\OpenERP S.A\Odoo\filestore\odoo-crm"
Get-ChildItem -Force -Recurse $root | Where-Object { $_.Name -like '*.__gc' } |
  ForEach-Object {
    if ($_.DirectoryName -like '*\checklist*') {
      Remove-Item -Force $_.FullName
    } else {
      $orig = $_.FullName -replace '\.__gc$', ''
      if (Test-Path $orig) { Remove-Item -Force $_.FullName }
      else { Rename-Item $_.FullName -NewName $_.Name.Replace('.__gc', '') }
    }
  }
```

Sau đó chạy lại test. Đây là lỗi filestore của Odoo trên Windows, không phải lỗi
nghiệp vụ của module.

### Debug nhanh

```powershell
cd odoo
# Xem log chi tiết
python odoo-bin -c odoo.conf --log-level=debug

# Mở shell ORM để thử code
python odoo-bin shell -c odoo.conf -d odoo-crm
```

Trong shell:

```python
env['company.approval.request'].search([])
env['company.approval.request'].create({'reason': 'Test', 'amount': 100})
env.cr.rollback()
```

---

## 12. Checklist module trước khi bàn giao

- [ ] `__manifest__.py`: `depends` đúng, `version` dạng `20.0.x.y.z`
- [ ] Model có `_description`, field có `string`
- [ ] `security/ir.access.csv` đủ quyền, có rule multi-company nếu cần
- [ ] Group/privilege đặt đúng chỗ, admin được gán
- [ ] View dùng `<list>`, `invisible=`, không `attrs`
- [ ] Menu/action có `groups` hợp lý
- [ ] Có test cho luồng chính + phân quyền
- [ ] Có `i18n/vi.po` cho chuỗi hiển thị
- [ ] Chạy `-u` trên bản copy DB không lỗi
- [ ] Backup trước khi deploy
- [ ] Commit vào git của dự án (không commit vào `odoo/`)

---

## 13. Chọn nghiệp vụ để làm module

Việc quyết định "yêu cầu này có cần module riêng không" thuộc
[Playbook phát triển module](odoo-module-playbook.md):

- §3 — bảng ánh xạ nghiệp vụ VN → object Odoo (mua hàng, kho, công nợ, lương,
  hóa đơn điện tử, Zalo/Facebook…).
- §2 — thang can thiệp, để biết khi nào chỉ cần cấu hình.
- §9 — checklist trước khi viết dòng code đầu tiên.

Không lặp lại danh sách nghiệp vụ ở đây để tránh hai nguồn sự thật.
