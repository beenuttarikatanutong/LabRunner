import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(
    page_title="Dashboard สะสมระยะวิ่ง",
    page_icon="🏃",
    layout="wide"
)

st.title("🏃 Dashboard สะสมระยะวิ่ง (15 ก.ค. - 15 ส.ค.)")
st.markdown("---")

st.sidebar.header("⚙️ การเชื่อมต่อข้อมูล")
sheet_url = st.sidebar.text_input(
    "ใส่ลิงก์ CSV ของ Google Sheet:",
    value="",
    placeholder="https://docs.google.com/spreadsheets/d/.../export?format=csv"
)

@st.cache_data(ttl=60)
def load_and_process_data(url):
    df_raw = pd.read_csv(url, header=None)
    
    # 8 รายชื่อตามลำดับใน Google Sheet
    members = ["พี่หนู", "บี", "พี่จัน", "พี่หยก", "จ๋า", "แดรงค์", "พี่แป๋ว", "อ้อน"]
    
    # ดึงคอลัมน์วันที่
    dates = df_raw.iloc[0, 2:].values
    
    # ดึงตารางรายวัน (แถว 1 ถึง 8)
    daily_matrix = df_raw.iloc[1:9, 2:].apply(pd.to_numeric, errors='coerce').fillna(0)
    
    # คำนวณระยะทางสะสมรวมจากวันวิ่งจริง
    totals = daily_matrix.sum(axis=1).values
    
    # ดึงเป้าหมายจากตารางด้านล่าง (แถว 10 ถึง 17 คอลัมน์ index 1)
    targets = pd.to_numeric(df_raw.iloc[10:18, 1].values, errors='coerce')
    targets = np.nan_to_num(targets, 0.0)
    
    # คำนวณระยะคงเหลือ
    remaining = targets - totals
    
    summary_df = pd.DataFrame({
        'ชื่อ': members,
        'ระยะสะสม (กม.)': np.round(totals, 2),
        'เป้าหมาย (กม.)': np.round(targets, 2),
        'ระยะคงเหลือ (กม.)': np.round(remaining, 2)
    })
    
    summary_df['เปอร์เซ็นต์ (%)'] = np.where(
        summary_df['เป้าหมาย (กม.)'] > 0,
        np.round((summary_df['ระยะสะสม (กม.)'] / summary_df['เป้าหมาย (กม.)'] * 100), 1),
        0.0
    )
    summary_df['สถานะ'] = summary_df['ระยะคงเหลือ (กม.)'].apply(lambda x: '🎯 ทะลุเป้าหมาย' if x <= 0 else '🏃 กำลังวิ่ง')
    
    daily_df = pd.DataFrame(daily_matrix.values, columns=dates)
    daily_df.insert(0, 'ชื่อ', members)
    
    return summary_df, daily_df

if sheet_url:
    try:
        summary_df, daily_df = load_and_process_data(sheet_url)
        
        # Metric Cards
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("👥 สมาชิกทั้งหมด", f"{len(summary_df)} คน")
        col2.metric("🎉 พิชิตเป้าหมายแล้ว", f"{(summary_df['ระยะคงเหลือ (กม.)'] <= 0).sum()} คน")
        col3.metric("🛣️ ระยะทางรวมทั้งหมด", f"{summary_df['ระยะสะสม (กม.)'].sum():.2f} กม.")
        col4.metric("🎯 เป้าหมายรวม", f"{summary_df['เป้าหมาย (กม.)'].sum():.2f} กม.")

        st.markdown("---")

        # Chart
        st.subheader("📊 การเปรียบเทียบระยะสะสมเทียบกับเป้าหมาย")
        fig = go.Figure()
        fig.add_trace(go.Bar(x=summary_df['ชื่อ'], y=summary_df['ระยะสะสม (กม.)'], name='ระยะสะสม (กม.)', marker_color='#2b5c8f'))
        fig.add_trace(go.Bar(x=summary_df['ชื่อ'], y=summary_df['เป้าหมาย (กม.)'], name='เป้าหมาย (กม.)', marker_color='#d9534f', opacity=0.6))
        fig.update_layout(barmode='group', xaxis_title="สมาชิก", yaxis_title="ระยะทาง (กม.)")
        st.plotly_chart(fig, use_container_width=True)

        # Summary Table
        st.subheader("📋 ตารางสรุปภาพรวมรายบุคคล")
        def highlight_status(val):
            color = '#d4edda' if 'ทะลุเป้าหมาย' in str(val) else '#fff3cd'
            return f'background-color: {color}'
            
        st.dataframe(summary_df.style.map(highlight_status, subset=['สถานะ']), use_container_width=True)

        st.markdown("---")

        # Member View
        st.subheader("👤 รายละเอียดการวิ่งรายบุคคล")
        selected_member = st.selectbox("เลือกสมาชิกที่ต้องการดูข้อมูล:", summary_df['ชื่อ'].unique())
        member_summary = summary_df[summary_df['ชื่อ'] == selected_member].iloc[0]
        member_daily = daily_df[daily_df['ชื่อ'] == selected_member]

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("ระยะสะสม", f"{member_summary['ระยะสะสม (กม.)']:.2f} กม.")
        m2.metric("เป้าหมาย", f"{member_summary['เป้าหมาย (กม.)']:.2f} กม.")
        rem_val = member_summary['ระยะคงเหลือ (กม.)']
        m3.metric("ระยะคงเหลือ", f"{0 if rem_val < 0 else rem_val:.2f} กม.", delta=f"เกินเป้า {-rem_val:.2f} กม." if rem_val < 0 else f"เหลือ {rem_val:.2f} กม.", delta_color="normal" if rem_val <= 0 else "inverse")
        m4.metric("ความคืบหน้า", f"{member_summary['เปอร์เซ็นต์ (%)']}%")

        st.progress(max(0.0, min(float(member_summary['เปอร์เซ็นต์ (%)']) / 100.0, 1.0)))

        # Daily Chart
        daily_melted = member_daily.melt(id_vars=['ชื่อ'], var_name='วันที่', value_name='ระยะทาง (กม.)')
        daily_melted['ระยะทาง (กม.)'] = pd.to_numeric(daily_melted['ระยะทาง (กม.)'], errors='coerce').fillna(0)
        daily_melted = daily_melted[daily_melted['ระยะทาง (กม.)'] > 0]

        if not daily_melted.empty:
            fig_daily = px.bar(daily_melted, x='วันที่', y='ระยะทาง (กม.)', text='ระยะทาง (กม.)', title=f"ประวัติการวิ่งของ {selected_member}")
            fig_daily.update_traces(texttemplate='%{text:.2f} กม.', textposition='outside')
            st.plotly_chart(fig_daily, use_container_width=True)
        else:
            st.info("ยังไม่มีข้อมูลการวิ่งรายวัน")

    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการโหลดข้อมูล: {e}")
else:
    st.warning("👈 กรุณาใส่ลิงก์ Google Sheet (CSV) ที่ Sidebar ด้านซ้ายมือเพื่อเริ่มใช้งาน")
