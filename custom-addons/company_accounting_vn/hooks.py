"""Gán tài khoản đối ứng cho bút toán đã ghi sổ có sẵn (cài module vào CSDL đã có dữ liệu)."""

BATCH_SIZE = 500


def backfill_counterparts(env, batch_size=BATCH_SIZE):
    """Tính lại Nợ TK / Có TK cho bút toán đã ghi sổ, theo lô, không đổi số tiền hay trạng thái.

    Chọn bằng MỘT truy vấn SQL: các bút toán đã ghi sổ có ít nhất một dòng kế toán (không phải dòng
    ghi chú, số tiền khác 0) chưa có mã đối ứng. Danh sách id cố định rồi mới chia lô nên không truy vấn
    lại mỗi lô. Chỉ ghi hai trường đối ứng, chạy lại bao nhiêu lần cũng cho cùng kết quả (idempotent).
    """
    env.flush_all()  # truy vấn SQL phải thấy các thay đổi chưa ghi xuống CSDL
    env.cr.execute("""
        SELECT DISTINCT move_id
          FROM account_move_line
         WHERE parent_state = 'posted'
           AND counterpart_name IS NULL
           AND COALESCE(display_type, '') NOT IN ('line_section', 'line_subsection', 'line_note')
           AND (debit <> 0 OR credit <> 0)
         ORDER BY move_id
    """)
    move_ids = [move_id for (move_id,) in env.cr.fetchall()]
    moves = env['account.move'].sudo().with_context(active_test=False)
    for start in range(0, len(move_ids), batch_size):
        batch = moves.browse(move_ids[start:start + batch_size])
        batch._compute_counterpart_accounts()
        batch.env.flush_all()
        batch.env.invalidate_all()  # giữ bộ nhớ ổn định giữa các lô


def post_init_hook(env):
    backfill_counterparts(env)
