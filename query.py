# -*- coding: utf-8 -*-
"""
@File    : query.py
@Time    : 2024/6/18 17:39
@Author  : lyq
@Description : 
"""
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Query Results", layout="wide")


@st.cache_data
def get_data():
    coding = pd.read_csv('results.csv', index_col=0, dtype={'学号': str})
    student_ids = coding.index.unique()
    to_drop_cols = ['序号', '英文姓名', '入学方式', '是否留学生', '专项计划', '修读类别', '选课方式']
    coding.drop(columns=to_drop_cols, inplace=True)

    homework = pd.read_csv('homework.csv', index_col=0, dtype={'学号': str})
    homework.drop(columns='姓名', inplace=True)
    return coding, homework, student_ids


def main():
    coding, homework, student_ids = get_data()
    student_id = st.sidebar.selectbox("学号", student_ids, index=10)
    st.sidebar.text_input('姓名', value=coding.loc[student_id]['姓名'], disabled=True)
    btn = st.sidebar.button("查询")

    if btn:
        coding_col, hw_col = st.columns(2, gap="medium")
        with coding_col:
            st.subheader("Coding")
            df = transform_student_row(coding.loc[student_id])
            st.dataframe(df, use_container_width=True, height=457)
        with hw_col:
            st.subheader("Homework")
            df = homework.loc[student_id]
            df.name = 'score'
            st.dataframe(df, use_container_width=True)


def transform_student_row(row):
    columns = row.index
    submissions = [col for col in columns if col.endswith('_submission') and 'Mid' not in col]
    submissions.sort(key=lambda x: x[-15:-11])
    prefixes = [col.rsplit('_', 1)[0] for col in submissions]
    results = [row[f'{prefix}_result'] for prefix in prefixes]
    results = map(lambda x: '✔' if x.isdigit() else x, results)
    data = {
        'submission': [row[f'{prefix}_submission'] for prefix in prefixes],
        'result': results
    }
    new_df = pd.DataFrame(data, index=prefixes)
    return new_df


if __name__ == '__main__':
    main()
