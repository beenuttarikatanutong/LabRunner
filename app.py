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
    "ใส่ลิงก์ CSV ของ Sheet 2:",
    value="",
    placeholder="https://docs.google.com/spreadsheets/d/.../export?format=csv&gid=..."
)

@st.cache_data(ttl=60)
def load_and_process_data(url):
    # อ่านข้อมูลจาก CSV
    df = pd.read_csv(url)
    
    # ทำความสะอาดชื่อคอลัมน์
    df.columns = [str(col).strip() for col in df.columns]
    
    # ระบุคอลัมน์หลัก
    name_col = df.columns[0]   # คอลัมน์แรก = ชื่อ
    target_col = df.columns[1] # คอลัมน์ที่สอง = เป้าหมาย
    
    # คอลัมน์ที่เป็นวันที่วิ่ง (ตั้งแต่คอลัมน์ที่ 3 เป็นต้นไป)
    date_cols = df.columns[2:]
    
    # แปลงตัวเลขการวิ่งรายวัน
    for col in date_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
    df[target_col] = pd.to_numeric(df[target_col], errors='coerce').fillna(0)
    
    # คำนวณระยะสะสมรวมจากทุกวันที่วิ่ง
    df['ระยะสะสม (กม.)'] = df[date_cols].sum(axis=1).round(2)
    df['เป้าหมาย (กม.)'] = df[target_col].round(2)
    df['ระยะคงเหลือ (กม.)'] = (df['เป้าหมาย (กม.)'] - df['ระยะสะสม (กม.)']).round(2)
    
    # คำนวณ %
    df['เปอร์เซ็นต์ (%)'] = np.where(
        df['เป้าหมาย (กม.)'] > 0,
        np.round((df['ระยะสะสม (กม.)'] / df['เป้าหมาย (กม.)'] * 100), 1),
        0.0
    )
    df['สถานะ'] = df['ระยะคงเหลือ (กม.)'].apply(lambda x: '🎯 ทะลุเป้าหมาย' if x <= 0 else '🏃 กำลังวิ่ง')
    
    # จัดคอลัมน์สรุป
    summary_df = df[[name_col, 'ระยะสะสม (กม.)', 'เป้าหมาย (กม.)', 'ระยะคงเหลือ (กม.)', 'เปอร์เซ็นต์ (%)', 'สถานะ']].copy()
    summary_df.rename(columns={name_col: 'ชื่อ'}, inplace=True)
    
    # ตารางประวัติรายวัน
    daily_df = df[[name_col] + list(date_cols)].copy()
    daily_df.rename(columns={name_col: 'ชื่อ'}, inplace=True)
    
    return summary_df, daily_df

if sheet_url:
    try:
        summary_df, daily_df = load_and_process_data(sheet_url)
        
        # 1. Metric Cards
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("👥 สมาชิกทั้งหมด", f"{len(summary_df)} คน")
        col2.metric("🎉 พิชิตเป้าหมายแล้ว", f"{(summary_df['ระยะคงเหลือ (กม.)'] <= 0).sum()} คน")
        col3.metric("🛣️ ระยะทางรวมทั้งหมด", f"{summary_df['ระยะสะสม (กม.)'].sum():.2f} กม.")
        col4.metric("🎯 เป้าหมายรวม", f"{summary_df['เป้าหมาย (กม.)'].sum():.2f} กม.")

        st.markdown("---")

        # 2. Chart
        st.subheader("📊 การเปรียบเทียบระยะสะสมเทียบกับเป้าหมาย")
        fig = go.Figure()
        fig.add_trace(go.Bar(x=summary_df['ชื่อ'], y=summary_df['ระยะสะสม (กม.)'], name='ระยะสะสม (กม.)', marker_color='#2b5c8f'))
        fig.add_trace(go.Bar(x=summary_df['ชื่อ'], y=summary_df['เป้าหมาย (กม.)'], name='เป้าหมาย (กม.)', marker_color='#d9534f', opacity=0.6))
        fig.update_layout(barmode='group', xaxis_title="สมาชิก", yaxis_title="ระยะทาง (กม.)")
        st.plotly_chart(fig, use_container_width=True)

        # 3. Summary Table
        st.subheader("📋 ตารางสรุปภาพรวมรายบุคคล")
        def highlight_status(val):
            color = '#d4edda' if 'ทะลุเป้าหมาย' in str(val) else '#fff3cd'
            return f'background-color: {color}'
            
        st.dataframe(summary_df.style.map(highlight_status, subset=['สถานะ']), use_container_width=True)

        st.markdown("---")

        # 4. Individual View
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
        st.error(f"เกิดข้อผิดพลาดในการอ่านข้อมูล: {e}")
        st.info("โปรดตรวจสอบว่าเลือกเผยแพร่เป็น CSV ของ 'ชีต 2' เรียบร้อยแล้ว")
else:
    st.warning("👈 กรุณาใส่ลิงก์ CSV ของ ชีต 2 ที่ Sidebar ด้านซ้ายมือเพื่อเริ่มใช้งาน")
