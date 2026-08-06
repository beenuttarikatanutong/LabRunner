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

@st.cache_data(ttl=30)
def load_and_process_data(url):
    # อ่านไฟล์ทั้งหมดแบบไม่กำหนด Header
    df_raw = pd.read_csv(url, header=None)
    
    # 1. ตรวจสอบว่าเป็นโครงสร้างตารางแยก 2 โซน (แบบชีตเดิม) หรือไม่
    is_2block = False
    if df_raw.shape[0] >= 18:
        cell_check = str(df_raw.iloc[9, 1])
        if 'เป้าหมาย' in cell_check or 'ระยะสะสม' in str(df_raw.iloc[9, 0]):
            is_2block = True

    if is_2block:
        # ดึงรายชื่อสมาชิก 8 คน
        members = df_raw.iloc[1:9, 1].astype(str).str.strip().tolist()
        dates = df_raw.iloc[0, 2:].astype(str).str.strip().tolist()
        
        # คำนวณระยะวิ่งรายวันและระยะสะสม
        daily_matrix = df_raw.iloc[1:9, 2:].apply(pd.to_numeric, errors='coerce').fillna(0)
        totals = daily_matrix.sum(axis=1).values
        
        # ดึงเป้าหมายจากโซนล่าง
        targets = pd.to_numeric(df_raw.iloc[10:18, 1].values, errors='coerce')
        targets = np.nan_to_num(targets, 0.0)
        
        summary_df = pd.DataFrame({
            'ชื่อ': members,
            'ระยะสะสม (กม.)': np.round(totals, 2),
            'เป้าหมาย (กม.)': np.round(targets, 2),
            'ระยะคงเหลือ (กม.)': np.round(targets - totals, 2)
        })
        daily_df = pd.DataFrame(daily_matrix.values, columns=dates)
        daily_df.insert(0, 'ชื่อ', members)
        
    else:
        # 2. กรณีเป็นโครงสร้างตารางเดียว (แบบชีต 2)
        header_row_idx = 0
        for idx, row in df_raw.iterrows():
            row_str = " ".join(row.dropna().astype(str))
            if any(k in row_str for k in ['ชื่อ', 'Name', 'สมาชิก', 'เป้าหมาย', 'Target']):
                header_row_idx = idx
                break
                
        df = pd.read_csv(url, header=header_row_idx).dropna(how='all')
        df = df.dropna(how='all', axis=1)
        df.columns = [str(c).strip() for c in df.columns]
        
        # ค้นหาคอลัมน์ชื่อ
        name_col = df.columns[0]
        for c in df.columns:
            if any(k in str(c).lower() for k in ['ชื่อ', 'name', 'สมาชิก']):
                name_col = c
                break
                
        # ค้นหาคอลัมน์เป้าหมาย
        target_col = None
        for c in df.columns:
            if any(k in str(c).lower() for k in ['เป้า', 'target', 'goal']):
                target_col = c
                break
                
        # แยกคอลัมน์ที่เป็นวันที่วิ่ง
        excl = ['รวม', 'สะสม', 'เป้า', 'คงเหลือ', '%', 'สถานะ', str(name_col)]
        if target_col:
            excl.append(str(target_col))
            
        date_cols = [c for c in df.columns if not any(k in str(c).lower() for k in excl)]
        
        # แปลงข้อมูลตัวเลข
        for c in date_cols:
            df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
            
        if target_col and target_col in df.columns:
            targets = pd.to_numeric(df[target_col], errors='coerce').fillna(0).values
        else:
            targets = np.zeros(len(df))
            
        totals = df[date_cols].sum(axis=1).values if date_cols else np.zeros(len(df))
        
        summary_df = pd.DataFrame({
            'ชื่อ': df[name_col].astype(str).str.strip(),
            'ระยะสะสม (กม.)': np.round(totals, 2),
            'เป้าหมาย (กม.)': np.round(targets, 2),
            'ระยะคงเหลือ (กม.)': np.round(targets - totals, 2)
        })
        
        daily_df = df[[name_col] + date_cols].copy()
        daily_df.rename(columns={name_col: 'ชื่อ'}, inplace=True)

    # คำนวณเปอร์เซ็นต์และสถานะ
    summary_df['เปอร์เซ็นต์ (%)'] = np.where(
        summary_df['เป้าหมาย (กม.)'] > 0,
        np.round((summary_df['ระยะสะสม (กม.)'] / summary_df['เป้าหมาย (กม.)'] * 100), 1),
        0.0
    )
    summary_df['สถานะ'] = summary_df['ระยะคงเหลือ (กม.)'].apply(lambda x: '🎯 ทะลุเป้าหมาย' if x <= 0 else '🏃 กำลังวิ่ง')
    
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

        # Bar Chart
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

        # Individual View
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
else:
    st.warning("👈 กรุณาใส่ลิงก์ Google Sheet (CSV) ที่ Sidebar ด้านซ้ายมือเพื่อเริ่มใช้งาน")
