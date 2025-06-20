import streamlit as st
import io
import json
import zipfile
import google.generativeai as genai

# ——— API 설정 ———
genai.configure(api_key="AIzaSyCW6ud9gZgT6tSqI9gMl2OhXweU_FT9CE0")
model = genai.GenerativeModel("gemini-1.5-flash")

st.title("📁 ZIP 업로드 기반 논문 분석 시스템")

# ZIP 파일 업로드 위젯
uploaded_zip = st.file_uploader(
    "논문 JSON 파일들이 들어있는 ZIP 파일을 업로드하세요:",
    type=["zip"]
)

# 질문 입력 및 버튼
question = st.text_input("AI에게 물어볼 질문을 입력하세요:")
ask = st.button("질문하기")

if uploaded_zip is not None and question and ask:
    try:
        # 스트림 포인터를 맨 앞으로
        uploaded_zip.seek(0)
        with zipfile.ZipFile(uploaded_zip) as z:
            context_list = []

            for name in z.namelist():
                # JSON 파일만 처리
                if not name.lower().endswith(".json"):
                    continue

                with z.open(name) as f:
                    data = json.load(f)

                # ① packages → gpt → sections 구조
                if (
                    isinstance(data, dict)
                    and "packages" in data
                    and isinstance(data["packages"], dict)
                    and "gpt" in data["packages"]
                ):
                    sections = data["packages"]["gpt"].get("sections", {})

                # ② 최상위에 sections 키가 있는 경우
                elif isinstance(data, dict) and "sections" in data:
                    sections = data.get("sections", {})

                # ③ pages 배열에 text가 있는 경우: 본문 전체를 abstract로 처리
                elif (
                    isinstance(data, dict)
                    and "pages" in data
                    and isinstance(data["pages"], list)
                ):
                    full_text = "\n\n".join(
                        page.get("text", "") for page in data["pages"]
                    )
                    sections = {
                        "title": data.get("file_name", name),
                        "abstract": full_text,
                        "methodology": "",
                        "results": "",
                    }

                # 알려진 구조가 아니면 스킵
                else:
                    continue

                # 실제로 뽑을 수 있는 내용만 가져오기
                title    = sections.get("title", "").strip()
                abstract = sections.get("abstract", "").strip()
                method   = sections.get("methodology", "").strip()
                result   = sections.get("results", "").strip()

                # 네 개 모두 비어 있으면 스킵
                if not (title or abstract or method or result):
                    continue

                context_list.append(
                    "📄 **파일:** {}\n\n"
                    f"**제목:** {title}\n\n"
                    f"**[초록]**\n{abstract}\n\n"
                    f"**[방법론]**\n{method}\n\n"
                    f"**[결과]**\n{result}\n".format(name)
                )

        if not context_list:
            st.warning("ZIP 파일 안에 처리 가능한 .json 논문 파일이 없습니다.")
        else:
            # 여러 논문 컨텍스트를 구분자와 함께 합치기
            full_context = "\n\n---\n\n".join(context_list)

            prompt = f"""
다음은 여러 논문에서 추출한 핵심 내용입니다. 이 내용을 바탕으로 아래 질문에 답해주세요.

{full_context}

[질문]
{question}
"""
            response = model.generate_content(prompt)

            st.subheader("🧠 AI의 응답:")
            st.write(response.text)

    except Exception as e:
        st.error(f"오류 발생: {str(e)}")
