"""
Gradio demo — FHE Customer Purchase Prediction
Step-by-step giống HF Space zama-fhe/encrypted_credit_scoring
"""

import subprocess
import time
import numpy as np
import gradio as gr

from backend.app.client.backend import (
    keygen_send,
    preprocess_encrypt_send,
    run_fhe,
    get_output_decrypt,
    run_end_to_end_flow,
)

# ── Bỏ khởi động FastAPI server tự động vì đã chạy container riêng ──────────

# ── UI ─────────────────────────────────────────────────────────────────────
with gr.Blocks(title="FHE Customer Predict") as demo:

    # ── Header ────────────────────────────────────────────────────────────
    gr.Markdown("""
# 🔐 Encrypted Customer Purchase Prediction
**Fully Homomorphic Encryption (FHE)** cho phép dự đoán trên dữ liệu đã mã hóa — server không bao giờ thấy thông tin thật của khách hàng.
""")

    gr.Markdown("""
<details>
<summary><b>FHE hoạt động như thế nào?</b></summary>

1. **Client** sinh cặp khóa: private key (giữ bí mật) + evaluation key (gửi server).
2. **Client** mã hóa dữ liệu bằng private key → gửi ciphertext lên server.
3. **Server** chạy mô hình trên ciphertext dùng evaluation key — không thấy plaintext.
4. **Client** nhận ciphertext kết quả về, giải mã bằng private key.

</details>
""")

    # hidden state lưu client_id
    client_id = gr.State(value="")

    # ── Step 1 ─────────────────────────────────────────────────────────────
    gr.Markdown("## Bước 1 — Sinh khóa")
    gr.Markdown(
        "_Private key_ dùng để mã hóa / giải mã, **không bao giờ rời khỏi client**. "
        "_Evaluation key_ gửi lên server để server tính toán trên ciphertext."
    )

    btn_keygen = gr.Button("🔑 Sinh khóa và gửi evaluation key lên server", variant="primary")
    txt_eval_key = gr.Textbox(label="Evaluation key (rút gọn):", interactive=False, max_lines=2)

    gr.Markdown("---")

    # ── Step 2 ─────────────────────────────────────────────────────────────
    gr.Markdown("## Bước 2 — Nhập thông tin khách hàng")
    gr.Markdown("Điền thông tin, nhấn **Mã hóa & Gửi** để encrypt và upload lên server.")

    with gr.Row():
        with gr.Column():
            inp_age = gr.Slider(
                minimum=18, maximum=100, value=60, step=1,
                label="Tuổi (Age)",
            )
            inp_income = gr.Number(
                value=99682.15,
                label="Thu nhập hàng năm (Annual Income)",
            )
            inp_purchases = gr.Slider(
                minimum=0, maximum=100, value=19, step=1,
                label="Số lần mua hàng (Number of Purchases)",
            )
            inp_time = gr.Number(
                value=22.59,
                label="Thời gian trên website (giờ)",
            )

        with gr.Column():
            inp_gender = gr.Radio(
                choices=[("Nam (1)", 1), ("Nữ (0)", 0)],
                value=1,
                label="Giới tính (Gender)",
            )
            inp_category = gr.Dropdown(
                choices=[("Category 1", 1), ("Category 2", 2),
                         ("Category 3", 3), ("Category 4", 4)],
                value=3,
                label="Danh mục sản phẩm (Product Category)",
            )
            inp_loyalty = gr.Radio(
                choices=[("Có (1)", 1), ("Không (0)", 0)],
                value=0,
                label="Tham gia Loyalty Program",
            )
            inp_discounts = gr.Slider(
                minimum=0, maximum=20, value=5, step=1,
                label="Số lần dùng khuyến mãi (Discounts Availed)",
            )

    btn_encrypt = gr.Button("🔒 Mã hóa & Gửi lên server", variant="primary")
    txt_enc_input = gr.Textbox(
        label="Encrypted input (rút gọn hex):",
        interactive=False, max_lines=2,
    )

    gr.Markdown("---")

    # ── Step 3 ─────────────────────────────────────────────────────────────
    gr.Markdown("## Bước 3 — Chạy FHE inference trên server")
    gr.Markdown(
        "Server nhận ciphertext, chạy mô hình **hoàn toàn trên dữ liệu đã mã hóa** "
        "dùng evaluation key. Server **không biết** kết quả là gì."
    )

    btn_run = gr.Button("⚙️ Chạy FHE inference", variant="primary")
    txt_fhe_time = gr.Textbox(
        label="Thời gian thực thi FHE (giây):",
        interactive=False, max_lines=1,
    )

    gr.Markdown("---")

    # ── Step 4 ─────────────────────────────────────────────────────────────
    gr.Markdown("## Bước 4 — Nhận kết quả & Giải mã")
    gr.Markdown(
        "Client nhận **ciphertext kết quả** từ server, "
        "dùng private key để giải mã ra dự đoán thật sự."
    )

    btn_decrypt = gr.Button("🔓 Nhận kết quả & Giải mã", variant="primary")

    with gr.Row():
        txt_enc_output = gr.Textbox(
            label="Encrypted output (rút gọn hex):",
            interactive=False, max_lines=2,
        )
        txt_prediction = gr.Textbox(
            label="Kết quả dự đoán:",
            interactive=False, max_lines=1,
        )

    gr.Markdown("---")
    
    gr.Markdown("## ⚡ Chạy toàn bộ luồng tự động (End-to-End Trace)")
    gr.Markdown(
        "Nhấn nút bên dưới để hệ thống tự lấy dữ liệu hiện tại (ở Bước 2) và tự động chạy một mạch từ **Bước 1 đến Bước 4**. "
        "Lựa chọn này giúp sinh ra 1 chuỗi trace toàn vẹn (End-to-end) trên Jaeger."
    )
    btn_e2e = gr.Button("🚀 Chạy một chạm (End-to-End)", variant="secondary")

    gr.Markdown("---")
    gr.Markdown(
        "_Demo được xây dựng với [Concrete-ML](https://github.com/zama-ai/concrete-ml) "
        "— Privacy-Preserving ML bởi [Zama](https://zama.ai/)._"
    )

    # ── Wiring ─────────────────────────────────────────────────────────────

    def _keygen(state_id):
        import numpy as np
        new_id = str(np.random.randint(0, 2**32))
        eval_key_short = keygen_send(new_id)
        return (
            new_id,
            eval_key_short,
            gr.update(value="✅ Đã sinh khóa và gửi evaluation key"),
        )

    btn_keygen.click(
        fn=_keygen,
        inputs=[client_id],
        outputs=[client_id, txt_eval_key, btn_keygen],
    )

    def _encrypt(cid, age, gender, income, purchases, category, time_web, loyalty, discounts):
        enc_short = preprocess_encrypt_send(
            cid, age, gender, income, purchases, category, time_web, loyalty, discounts
        )
        return enc_short, gr.update(value="✅ Đã mã hóa và gửi lên server")

    btn_encrypt.click(
        fn=_encrypt,
        inputs=[
            client_id,
            inp_age, inp_gender, inp_income, inp_purchases,
            inp_category, inp_time, inp_loyalty, inp_discounts,
        ],
        outputs=[txt_enc_input, btn_encrypt],
    )

    def _run(cid):
        elapsed = run_fhe(cid)
        return elapsed, gr.update(value=f"✅ FHE inference hoàn tất ({elapsed})")

    btn_run.click(
        fn=_run,
        inputs=[client_id],
        outputs=[txt_fhe_time, btn_run],
    )

    def _decrypt(cid):
        label, enc_out_short = get_output_decrypt(cid)
        return enc_out_short, label, gr.update(value="✅ Đã giải mã kết quả")

    btn_decrypt.click(
        fn=_decrypt,
        inputs=[client_id],
        outputs=[txt_enc_output, txt_prediction, btn_decrypt],
    )

    def _run_e2e(age, gender, income, purchases, category, time_web, loyalty, discounts):
        new_client_id, eval_key, enc_input, elapsed, enc_out, label = run_end_to_end_flow(
            age, gender, income, purchases, category, time_web, loyalty, discounts
        )
        return (
            new_client_id, 
            eval_key, 
            gr.update(value="✅ Đã sinh khóa và gửi evaluation key"),
            enc_input, 
            gr.update(value="✅ Đã mã hóa và gửi lên server"),
            elapsed, 
            gr.update(value=f"✅ FHE inference hoàn tất ({elapsed})"),
            enc_out, 
            label, 
            gr.update(value="✅ Chạy End-to-End xong!")
        )

    btn_e2e.click(
        fn=_run_e2e,
        inputs=[
            inp_age, inp_gender, inp_income, inp_purchases,
            inp_category, inp_time, inp_loyalty, inp_discounts,
        ],
        outputs=[
            client_id, txt_eval_key, btn_keygen,
            txt_enc_input, btn_encrypt,
            txt_fhe_time, btn_run,
            txt_enc_output, txt_prediction, btn_decrypt
        ]
    )


if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860, share=False)
