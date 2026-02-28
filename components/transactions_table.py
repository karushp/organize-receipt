"""Table display of all transactions with edit/delete options."""

import streamlit as st


def render_transactions_table(transactions: list[dict], on_delete):
    """
    Render the transactions table with delete buttons.
    on_delete: callback(transaction_id)
    """
    if not transactions:
        st.info("No receipts recorded yet. Add one above!")
        return

    st.subheader("Transactions")

    for tx in transactions:
        with st.container():
            col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
            with col1:
                st.write(f"**{tx.get('item', '')}**")
                st.caption(f"{tx.get('date', '')} · {tx.get('category', '')}")
            with col2:
                amount = tx.get("amount", "")
                st.write(f"${float(amount):.2f}" if amount else "—")
            with col3:
                if tx.get("drive_file_id"):
                    st.markdown(
                        f"[📷 View](https://drive.google.com/file/d/{tx['drive_file_id']}/view)"
                    )
            with col4:
                if st.button("Delete", key=f"del_{tx.get('id', '')}", type="secondary"):
                    try:
                        on_delete(tx["id"])
                        st.success("Deleted.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Delete failed: {e}")

            st.divider()
