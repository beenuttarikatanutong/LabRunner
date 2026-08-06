import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# ตั้งค่าหน้าเว็บ
st.set_page_config(
    page_title="Dashboard สะสมระยะวิ่ง",
    page_icon="🏃",
    layout="wide"
)

# หัวข้อหลัก
st.title("🏃 Dashboard สะสมระยะวิ่ง (15 ก.ค. - 15 ส.ค.)")
st.markdown("---")

st.sidebar.header("⚙️ การเชื่อมต่อข้อมูล")
sheet_url = st.sidebar.text_input(
    "ใส่ลิงก์ CSV ของ Google Sheet:",
    value="",
    placeholder="https://docs.google.com/spreadsheets/d/.../export?format=csv"
)

st.sidebar.info(
    "💡 **วิธีเอาลิงก์จาก Google Sheets:**\n"
    "1. เปิด Google Sheet\n"
    "2. ไปที่ `ไฟล์ (File)` -> `แชร์ (Share)` -> `เผยแพร่ไปยังเว็บ (Publish to web)`\n"
    "3. เลือกแผ่นงาน และเลือกรูปแบบเป็น `CSV` แล้วคัดลอกลิงก์มาวาง"
)

# ฟังก์ชันประมวลผลข้อมูล
@st.cache_data(ttl=60)
def load_and_process_data(url):
    # อ่านไฟล์โดยไม่ใช้ header อัตโนมัติ เพื่อป้องกันการเยื้องของคอลัมน์
    df = pd.read_csv(url, header=None)
    
    # รายชื่อสมาชิกทั้ง 8 คนตามลำดับในไฟล์
    members = ["พี่หนู", "บี", "พี่จัน", "พี่หยก", "จ๋า", "แดรงค์", "พี่แป๋ว", "อ้อน"]
    
    # ดึงคอลัมน์วันที่วิ่ง (แถวที่ 0 คอลัมน์ที่ 2 เป็นต้นไป)
    dates = df.iloc[0, 2:].values
    
    # ดึงข้อมูลระยะวิ่งรายวันของสมาชิกแต่ละคน (แถวที่ 1 ถึง 8 คอลัมน์ที่ 2 เป็นต้นไป)
    daily_matrix = df.iloc[1:9, 2:].apply(pd.to_numeric, errors='coerce').fillna(0)
    
    # ดึงเป้าหมายของสมาชิกแต่ละคน (แถวที่ 10 ถึง 17 คอลัมน์ที่ 1)
    targets = pd.to_numeric(df.iloc[10:18, 1].values, errors='coerce')
    
    # คำนวณระยะทางสะสมจริงจากการวิ่งรายวัน
    totals = daily_matrix.sum(axis=1).values
    
    # คำนวณระยะคงเหลือ
    remaining = targets - totals
    
    # สร้าง DataFrame สรุปผล
    summary_df = pd.DataFrame({
        'ชื่อ': members,
        'ระยะสะสม (กม.)': totals,
        'เป้าหมาย (กม.)': targets,
        'ระยะคงเหลือ (กม.)': remaining
    })
    
    # คำนวณ % ความคืบหน้า
    summary_df['เปอร์เซ็นต์ (%)'] = np.where(
        summary_df['เป้าหมาย (กม.)'] > 0,
        (summary_df['ระยะสะสม (กม.)'] / summary_df['เป้าหมาย (กม.)'] * 100).round(1),
        0.0
    )
    summary_df['สถานะ'] = summary_df['ระยะคงเหลือ (กม.)'].apply(lambda x: '🎯 ทะลุเป้าหมาย' if x <= 0 else '🏃 กำลังวิ่ง')
    
    # สร้าง DataFrame สำหรับประวัติรายวัน
    daily_df = pd.DataFrame(daily_matrix.values, columns=dates)
    daily_df.insert(0, 'ชื่อ', members)
    
    return summary_df, daily_df

# การแสดงผล
if sheet_url:
    try:
        summary_df, daily_df = load_and_process_data(sheet_url)
        
        # 1. Summary Cards (KPI Metrics)
        total_runners = len(summary_df)
        completed_runners = (summary_df['ระยะคงเหลือ (กม.)'] <= 0).sum()
        total_distance = summary_df['ระยะสะสม (กม.)'].sum()
        total_target = summary_df['เป้าหมาย (กม.)'].sum()

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("👥 สมาชิกทั้งหมด", f"{total_runners} คน")
        col2.metric("🎉 พิชิตเป้าหมายแล้ว", f"{completed_runners} คน")
        col3.metric("🛣️ ระยะทางรวมทั้งหมด", f"{total_distance:.2f} กม.")
        col4.metric("🎯 เป้าหมายรวม", f"{total_target:.2f} กม.")

        st.markdown("---")

        # 2. กราฟเปรียบเทียบระยะสะสม vs เป้าหมาย
        st.subheader("📊 การเปรียบเทียบระยะสะสมเทียบกับเป้าหมาย")
        
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=summary_df['ชื่อ'],
            y=summary_df['ระยะสะสม (กม.)'],
            name='ระยะสะสม (กม.)',
            marker_color='#2b5c8f'
        ))
        fig.add_trace(go.Bar(
            x=summary_df['ชื่อ'],
            y=summary_df['เป้าหมาย (กม.)'],
            name='เป้าหมาย (กม.)',
            marker_color='#d9534f',
            opacity=0.6
        ))
        fig.update_layout(barmode='group', xaxis_title="สมาชิก", yaxis_title="ระยะทาง (กม.)")
        st.plotly_chart(fig, use_container_width=True)

        # 3. ตารางสรุปภาพรวม
        st.subheader("📋 ตารางสรุปภาพรวมรายบุคคล")
        
        def highlight_status(val):
            color = '#d4edda' if 'ทะลุเป้าหมาย' in str(val) else '#fff3cd'
            return f'background-color: {color}'

        st.dataframe(
            summary_df.style.map(highlight_status, subset=['สถานะ']),
            use_container_width=True
        )

        st.markdown("---")

        # 4. เจาะลึกรายบุคคล (Individual View)
        st.subheader("👤 รายละเอียดการวิ่งรายบุคคล")
        selected_member = st.selectbox("เลือกสมาชิกที่ต้องการดูข้อมูล:", summary_df['ชื่อ'].unique())

        member_summary = summary_df[summary_df['ชื่อ'] == selected_member].iloc[0]
        member_daily = daily_df[daily_df['ชื่อ'] == selected_member]

        m_col1, m_col2, m_col3, m_col4 = st.columns(4)
        m_col1.metric("ระยะสะสม", f"{member_summary['ระยะสะสม (กม.)']:.2f} กม.")
        m_col2.metric("เป้าหมาย", f"{member_summary['เป้าหมาย (กม.)']:.2f} กม.")
        
        rem_val = member_summary['ระยะคงเหลือ (กม.)']
        m_col3.metric(
            "ระยะคงเหลือ", 
            f"{0 if rem_val < 0 else rem_val:.2f} กม.",
            delta=f"เกินเป้า {-rem_val:.2f} กม." if rem_val < 0 else f"เหลือ {rem_val:.2f} กม.",
            delta_color="normal" if rem_val <= 0 else "inverse"
        )
        m_col4.metric("ความคืบหน้า", f"{member_summary['เปอร์เซ็นต์ (%)']}%")

        # Progress bar
        raw_pct = member_summary['เปอร์เซ็นต์ (%)']
        pct_float = 0.0 if (pd.isna(raw_pct) or np.isinf(raw_pct)) else float(raw_pct)
        progress = max(0.0, min(pct_float / 100.0, 1.0))
        st.progress(progress)

        # ประวัติการวิ่งแต่ละวันของสมาชิก
        st.markdown(f"**ประวัติการวิ่งแต่ละวันของ {selected_member}:**")
        
        daily_melted = member_daily.melt(id_vars=['ชื่อ'], var_name='วันที่', value_name='ระยะทาง (กม.)')
        daily_melted = daily_melted[daily_melted['ระยะทาง (กม.)'] > 0]

        if not daily_melted.empty:
            fig_daily = px.bar(
                daily_melted, 
                x='วันที่', 
                y='ระยะทาง (กม.)', 
                text='ระยะทาง (กม.)',
                title=f"ประวัติการวิ่งของ {selected_member}"
            )
            fig_daily.update_traces(texttemplate='%{text:.2f} กม.', textposition='outside')
            st.plotly_chart(fig_daily, use_container_width=True)
        else:
            st.info("ยังไม่มีข้อมูลการวิ่งรายวัน")

    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการโหลดข้อมูล: {e}")
        st.info("โปรดตรวจสอบว่าลิงก์ Google Sheet ถูกต้องและตั้งค่าให้เผยแพร่เป็น CSV เรียบร้อยแล้ว")
else:
    st.warning("👈 กรุณาใส่ลิงก์ Google Sheet (CSV) ที่ Sidebar ด้านซ้ายมือเพื่อเริ่มใช้งาน")
