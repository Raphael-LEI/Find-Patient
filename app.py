import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import re
import random

# ==========================================
# 0. 产品定义与声明
# ==========================================
VERSION = "v1.0-MVP"
SLOGAN = "🎯 一分钟找到你想研究的患者"
MATURITY_NOTE = """
**当前版本能力边界声明：**
1. **检索逻辑**：基于关键词加权评分，暂不支持深度语义推理。
2. **数据规模**：针对 1,000 例以内脱敏数据进行了性能优化。
3. **临床关键词识别**：支持药名、疾病、分期、生物标志物等核心因子提取。
4. **安全级别**：本地内存计算模式，数据关闭即焚，严禁上传未脱敏隐私数据。
"""

@st.cache_data
def get_mock_data():
    data = []
    scenes = [
        ("IM", "患者高龄房颤病史，长期口服华法林。主诉：消化道出血、黑便。INR升高。", 80, 1, "男"),
        ("ON", "非小细胞肺癌，基因检测EGFR突变(+)。临床分期T4N2M0。预后风险高。", 65, 1, "女"),
        ("SG", "结肠腺癌手术后。病理报告：低分化。淋巴结转移发现N2级。高风险复发。", 55, 1, "男"),
        ("IO", "胃癌患者。分子检测dMMR。行新辅助免疫治疗。病理缓解明显，生存获益显著。", 62, 0, "女")
    ]
    for prefix, content, age_base, status, sex_pref in scenes:
        for i in range(1, 21):
            id_val = f"{prefix}-{i:03}"
            sex = sex_pref if random.random() > 0.2 else ("女" if sex_pref=="男" else "男")
            data.append({
                "ID": id_val, "年龄": age_base + random.randint(-5, 5), "性别": sex,
                "content": content, "survival": random.randint(5, 70), "status": status,
                "full_record": f"【系统存根 - {id_val}】\n原始临床记录：{content}\n辅助检查：指标异常详见原始报告。随访计划：按临床指南定期复查。"
            })
    for i in range(1, 101):
        data.append({
            "ID": f"B-{i:03}", "年龄": random.randint(30, 80), "性别": random.choice(["男", "女"]),
            "content": "常规临床随访病例。目前病情稳定，预后良好。", "survival": random.randint(60, 90), "status": 0,
            "full_record": "常规体检及术后复查记录。"
        })
    return pd.DataFrame(data)

def smart_ranked_search(df, query):
    if not query: return pd.DataFrame(), []
    # 临床核心因子库
    med_library = ["华法林", "房颤", "消化道出血", "黑便", "肺癌", "EGFR", "T4", "结肠", "淋巴结", "N", "低分化", "胃癌", "新辅助", "dMMR", "免疫"]
    found_keywords = [m for m in med_library if m.upper() in query.upper()]
    if not found_keywords:
        found_keywords = [k for k in query.split() if len(k) > 1]
    
    def calculate_score(row):
        text = str(row['content']).upper()
        score = sum(3 for k in found_keywords if k.upper() in text)
        if "N" in found_keywords and ("N1" in text or "N2" in text): score += 2
        nums = re.findall(r'\d+', query)
        for n in nums:
            if n in str(row['年龄']): score += 1
        return score
    
    df_copy = df.copy()
    df_copy['score'] = df_copy.apply(calculate_score, axis=1)
    res = df_copy[df_copy['score'] > 0].sort_values(by='score', ascending=False).copy()
    res['display_index'] = range(1, len(res) + 1)
    return res, found_keywords

def main():
    st.set_page_config(page_title="Find Patient", layout="wide")
    st.markdown("<style>.patient-card { padding: 18px; border-radius: 8px; border-left: 5px solid #FF4B4B; background-color: #f8f9fa; margin-bottom: 12px; border: 1px solid #eee; } .index-badge { background-color: #FF4B4B; color: white; padding: 2px 8px; border-radius: 4px; font-weight: bold; } .keyword-tag { background-color: #E1E4E8; color: #0366D6; padding: 2px 6px; border-radius: 12px; font-size: 0.8em; margin-right: 5px; font-weight: 500; }</style>", unsafe_allow_html=True)
    
    st.title("Find Patient 医溯")
    st.markdown(f"### {SLOGAN}")
    
    # --- 侧边栏 ---
    st.sidebar.title("📁 数据中心")
    with st.sidebar.expander("🛠️ 系统能力边界说明", expanded=True):
        st.write(MATURITY_NOTE)
    
    template_df = pd.DataFrame({"ID":["P001"],"年龄":[65],"性别":["男"],"content":["此处输入病历文本..."],"survival":[24],"status":[1]})
    st.sidebar.download_button("📥 下载标准数据模板", template_df.to_csv(index=False).encode('utf-8-sig'), "template.csv")
    
    uploaded_file = st.sidebar.file_uploader("上传脱敏科研数据 (xlsx/csv)", type=["xlsx", "csv"])
    df_all = get_mock_data()
    if uploaded_file:
        try:
            if uploaded_file.name.endswith('xlsx'): df_all = pd.read_excel(uploaded_file)
            else:
                try: df_all = pd.read_csv(uploaded_file, encoding='utf-8-sig')
                except: df_all = pd.read_csv(uploaded_file, encoding='gbk')
            st.sidebar.success("✅ 数据加载成功")
        except:
            st.sidebar.error("❌ 读取失败，已切换回模拟数据")

    st.sidebar.divider()
    st.sidebar.subheader("🤝 合作与交流")
    st.sidebar.info("如有功能建议或搜索优化需求，请**联系雷雷**。具体的联系方式请参阅 GitHub 项目主页的 README 文档。")

    # --- 主界面 ---
    user_query = st.text_input("💬 请描述您的科研需求:", placeholder="例如：我想找找75岁以上用华法林出血的房颤病人...")
    df_match, active_ks = smart_ranked_search(df_all, user_query)
    df_others = df_all[~df_all.index.isin(df_match.index)]

    if user_query:
        if not df_match.empty:
            # 展示识别到的关键词
            kw_html = "".join([f'<span class="keyword-tag"># {k}</span>' for k in active_ks])
            st.markdown(f"**检测到临床因子：** {kw_html}", unsafe_allow_html=True)
            
            st.success(f"已锁定 {len(df_match)} 例符合要求的患者")
            
            c1, c2 = st.columns([1.5, 1])
            with c1:
                fig_km = go.Figure()
                def add_km(sub_df, name, color):
                    if sub_df.empty: return
                    sub_df = sub_df.sort_values("survival")
                    n, t, p, curr = len(sub_df), [0], [1.0], 1.0
                    for i in range(n):
                        t.append(sub_df.iloc[i]["survival"])
                        if sub_df.iloc[i]["status"] == 1: curr *= (n - i - 1) / (n - i) if (n-i)>0 else 0
                        p.append(curr)
                    fig_km.add_trace(go.Scatter(x=t, y=p, name=name, line=dict(shape='hv', width=4, color=color)))
                add_km(df_match, "筛选队列", "#FF4B4B")
                add_km(df_others, "背景对照", "#2CA02C")
                fig_km.update_layout(title="生存率分析 (KM-Curve)", template="plotly_white")
                st.plotly_chart(fig_km, use_container_width=True)
            with c2:
                st.write("**人群画像**")
                m1, m2 = st.columns(2)
                m1.metric("入组比例", f"{(len(df_match)/len(df_all)*100):.1f}%")
                m2.metric("平均年龄", f"{df_match['年龄'].mean():.1f}岁")
                t1, t2 = st.tabs(["性别占比", "年龄分布"])
                with t1: st.plotly_chart(px.pie(df_match, names='性别', hole=0.4, color_discrete_sequence=['#FF4B4B', '#2CA02C']).update_layout(margin=dict(t=0,b=0,l=0,r=0), height=250), use_container_width=True)
                with t2: st.plotly_chart(px.histogram(df_match, x='年龄', template="plotly_white", color_discrete_sequence=['#FF4B4B']).update_layout(margin=dict(t=0,b=0,l=0,r=0), height=250), use_container_width=True)

            st.divider()
            st.subheader("📋 匹配详情（高亮显示识别到的临床关键词）")
            for _, row in df_match.iterrows():
                content = row['content']
                for k in active_ks: 
                    content = content.replace(k, f'<mark style="background-color:#FF4B4B;color:white;padding:0 2px;">{k}</mark>')
                st.markdown(f'<div class="patient-card"><span class="index-badge">序号 {int(row["display_index"])}</span> <b>ID:</b> {row["ID"]} | <b>相关性得分:</b> {row["score"]}<p style="margin-top:8px; line-height:1.6;">{content}</p></div>', unsafe_allow_html=True)
                with st.expander(f"📑 核对原始病历存根"):
                    st.text_area("详细记录", value=row.get('full_record', '暂无记录'), height=100, disabled=True)
        else: st.error("未能匹配到相关患者。")
    else: st.info("💡 请在上方输入筛选条件，或在左侧上传脱敏数据集。")

if __name__ == "__main__":
    main()
    