def normalize_string(s):
    """유니코드 정규화"""
    return unicodedata.normalize('NFC', s)

def format_docs(docs):
    """검색된 문서들을 하나의 문자열로 포맷팅"""
    context = ""
    for doc in docs:
        context += doc.page_content
        context += '\n'
    return context

# 결과를 저장할 리스트 초기화
results = []

# DataFrame의 각 행에 대해 처리
for _, row in tqdm(df.iterrows(), total=len(df), desc="Answering Questions"):
    # 소스 문자열 정규화
    source = normalize_string(row['Source'])
    question = row['Question']

    # 정규화된 키로 데이터베이스 검색
    normalized_keys = {normalize_string(k): v for k, v in pdf_databases.items()}
    retriever = normalized_keys[source]['retriever']

    # RAG 체인 구성
    template = """
    다음 정보를 바탕으로 질문에 답하세요:
    {context}

    질문: {question}

    주어진 질문에만 답변하세요. 문장으로 답변해주세요. 답변할 때 질문의 주어를 써주세요.
    답변:
    """
    prompt = PromptTemplate.from_template(template)

    # RAG 체인 정의
    rag_chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )

    # 답변 추론
    print(f"Question: {question}")
    full_response = rag_chain.invoke(question)

    print(f"Answer: {full_response}\n")

    # 결과 저장
    results.append({
        "Source": row['Source'],
        "Source_path": row['Source_path'],
        "Question": question,
        "Answer": full_response
    })
