import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(
    page_title="Dashboard สะสมระยะวิ่ง (ชีต 1)",
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

@st.cache_data(ttl=10)
def load_and_process_sheet1(url):
    df_raw = pd.read_csv(url, header=None)
    
    # 1. ค้นหาแถวแบ่งโซนข้อมูล ("ระยะสะสม" หรือ "เป้าหมาย") แบบ Dynamic
    sep_idx = None
    for idx, row in df_raw.iterrows():
        row_str = " ".join(row.dropna().astype(str))
        if 'ระยะสะสม' in row_str or 'เป้าหมาย' in row_str:
            sep_idx = idx
            break
            
    if sep_idx is None:
        sep_idx = len(df_raw) // 2

    # 2. ดึงรายชื่อสมาชิกที่มีอยู่จริง (ตั้งแต่แถวที่ 1 ถึงก่อนแถวแบ่งโซน)
    members = df_raw.iloc[1:sep_idx, 1].dropna().astype(str).str.strip().tolist()
    members = [m for m in members if m != '' and m.lower() != 'nan']
    n_members = len(members)

    # 3. ดึงวันที่ทั้งหมดจากแถวแรก (คอลัมน์ Index 2 เป็นต้นไป)
    header_row = df_raw.iloc[0, 2:].dropna().astype(str).str.strip().tolist()
    dates = [d for d in header_row if d != '' and d.lower() != 'nan']
    n_dates = len(dates)

    # 4. ดึงตารางระยะวิ่งรายวันเฉพาะคอลัมน์ที่มีวันที่ และคำนวณระยะสะสมจริง
    daily_matrix = df_raw.iloc[1:1+n_members, 2:2+n_dates].apply(pd.to_numeric, errors='coerce').fillna(0)
    totals = daily_matrix.sum(axis=1).values

    # 5. ดึงเป้าหมายจากตารางส่วนล่างตามจำนวนสมาชิกที่มีจริง
    raw_targets = df_raw.iloc[sep_idx+1 : sep_idx+1+n_members, 1].values
    targets = pd.to_numeric(pd.Series(raw_targets), errors='coerce').fillna(0).values

    # ปรับขนาด Array เป้าหมายให้ตรงกับจำนวนสมาชิกเสมอ
    if len(targets) < n_members:
        targets = np.pad(targets, (0, n_members - len(targets)), 'constant', constant_values=0)
    elif len(targets) > n_members:
        targets = targets[:n_members]

    # จัดทำ Summary DataFrame
    summary_df = pd.DataFrame({
        'ชื่อ': members,
        'ระยะสะสม (กม.)': np.round(totals, 2),
        'เป้าหมาย (กม.)': np.round(targets, 2),
        'ระยะคงเหลือ (กม.)': np.round(targets - totals, 2)
    })
    
    # คำนวณเปอร์เซ็นต์
    summary_df['เปอร์เซ็นต์ (%)'] = np.where(
        summary_df['เป้าหมาย (กม.)'] > 0,
        np.round((summary_df['ระยะสะสม (กม.)'] / summary_df['เป้าหมาย (กม.)'] * 100), 2),
        0.00
    )
    summary_df['สถานะ'] = summary_df['ระยะคงเหลือ (กม.)'].apply(
        lambda x: '🎯 ทะลุเป้าหมาย' if x <= 0 else '🏃 กำลังวิ่ง'
    )
    
    # จัดทำ Daily DataFrame
    daily_df = pd.DataFrame(daily_matrix.values, columns=dates)
    daily_df.insert(0, 'ชื่อ', members)
    
    return summary_df, daily_df

if sheet_url:
    try:
        summary_df, daily_df = load_and_process_sheet1(sheet_url)
        
        # Metric Cards
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("👥 สมาชิกทั้งหมด", f"{len(summary_df)} คน")
        col2.metric("🎉 พิชิตเป้าหมายแล้ว", f"{(summary_df['ระยะคงเหลือ (กม.)'] <= 0).sum()} คน")
        col3.metric("🛣️ ระยะทางรวมทั้งหมด", f"{summary_df['ระยะสะสม (กม.)'].sum():.2f} กม.")
        col4.metric("🎯 เป้าหมายรวม", f"{summary_df['เป้าหมาย (กม.)'].sum():.2f} กม.")

        st.markdown("---")

        # 1. กราฟแท่งเปรียบเทียบระยะสะสม vs เป้าหมาย
        st.subheader("📊 การเปรียบเทียบระยะสะสมเทียบกับเป้าหมาย")
        fig_bar = go.Figure()
        
        fig_bar.add_trace(go.Bar(
            x=summary_df['ชื่อ'],
            y=summary_df['ระยะสะสม (กม.)'],
            name='ระยะสะสม (กม.)',
            marker_color='#2b5c8f',
            text=summary_df['ระยะสะสม (กม.)'].map('{:.2f}'.format),
            textposition='outside'
        ))
        
        fig_bar.add_trace(go.Bar(
            x=summary_df['ชื่อ'],
            y=summary_df['เป้าหมาย (กม.)'],
            name='เป้าหมาย (กม.)',
            marker_color='#d9534f',
            opacity=0.6,
            text=summary_df['เป้าหมาย (กม.)'].map('{:.2f}'.format),
            textposition='outside'
        ))
        
        fig_bar.update_layout(
            barmode='group',
            xaxis_title="สมาชิก",
            yaxis_title="ระยะทาง (กม.)",
            legend_title="ประเภทข้อมูล"
        )
        st.plotly_chart(fig_bar, use_container_width=True)

        st.markdown("---")

        # 2. กราฟเส้นพัฒนาการวิ่งรายวัน
        st.subheader("📈 พัฒนาการวิ่งรายวันรวม")
        
        daily_long = daily_df.melt(id_vars=['ชื่อ'], var_name='วันที่', value_name='ระยะทาง (กม.)')
        daily_long['ระยะทาง (กม.)'] = pd.to_numeric(daily_long['ระยะทาง (กม.)'], errors='coerce').fillna(0)
        
        fig_line = px.line(
            daily_long,
            x='วันที่',
            y='ระยะทาง (กม.)',
            color='ชื่อ',
            markers=True,
            title="สถิติระยะวิ่งรายวันของสมาชิกทุกคน"
        )
        fig_line.update_traces(hovertemplate='<b>%{x}</b><br>วิ่งได้: %{y:.2f} กม.')
        fig_line.update_layout(xaxis_title="วันที่", yaxis_title="ระยะทาง (กม.)")
        st.plotly_chart(fig_line, use_container_width=True)

        st.markdown("---")

        # 3. ตารางสรุปภาพรวม
        st.subheader("📋 ตารางสรุปภาพรวมรายบุคคล")
        
        def highlight_status(val):
            color = '#d4edda' if 'ทะลุเป้าหมาย' in str(val) else '#fff3cd'
            return f'background-color: {color}'

        formatted_df = summary_df.copy()
        for col in ['ระยะสะสม (กม.)', 'เป้าหมาย (กม.)', 'ระยะคงเหลือ (กม.)', 'เปอร์เซ็นต์ (%)']:
            formatted_df[col] = formatted_df[col].apply(lambda x: f"{x:.2f}")

        st.dataframe(formatted_df.style.map(highlight_status, subset=['สถานะ']), use_container_width=True)

        st.markdown("---")

        # 4. รายละเอียดรายบุคคล
        st.subheader("👤 รายละเอียดการวิ่งรายบุคคล")
        selected_member = st.selectbox("เลือกสมาชิกที่ต้องการดูข้อมูล:", summary_df['ชื่อ'].unique())
        member_summary = summary_df[summary_df['ชื่อ'] == selected_member].iloc[0]

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("ระยะสะสม", f"{member_summary['ระยะสะสม (กม.)']:.2f} กม.")
        m2.metric("เป้าหมาย", f"{member_summary['เป้าหมาย (กม.)']:.2f} กม.")
        rem_val = member_summary['ระยะคงเหลือ (กม.)']
        m3.metric(
            "ระยะคงเหลือ",
            f"{0.00 if rem_val < 0 else rem_val:.2f} กม.",
            delta=f"เกินเป้า {-rem_val:.2f} กม." if rem_val < 0 else f"เหลือ {rem_val:.2f} กม.",
            delta_color="normal" if rem_val <= 0 else "inverse"
        )
        m4.metric("ความคืบหน้า", f"{member_summary['เปอร์เซ็นต์ (%)']:.2f}%")

        st.progress(max(0.0, min(float(member_summary['เปอร์เซ็นต์ (%)']) / 100.0, 1.0)))

    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการดึงข้อมูลจาก ชีต 1: {e}")
else:
    st.warning("👈 กรุณาใส่ลิงก์ Google Sheet (CSV) ที่ Sidebar ด้านซ้ายมือเพื่อเริ่มใช้งาน")
