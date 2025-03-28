def setup_llm_pipeline(fine_tune=False, training_data=None):
    # 4비트 양자화 설정
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16
    )

    # 모델 ID
    model_id = "rtzr/ko-gemma-2-9b-it"

    # 토크나이저 로드 및 설정
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    tokenizer.use_default_system_prompt = False

    # 모델 로드 및 양자화 설정 적용
    model = Gemma2ForCausalLM.from_pretrained(
        model_id,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True
    )

    if fine_tune and training_data:
        # LoRA 설정 추가
        lora_config = LoraConfig(
            r=8,
            lora_alpha=16,
            lora_dropout=0.1,
            target_modules=["q_proj", "v_proj"],
            task_type=TaskType.CAUSAL_LM
        )
        model = get_peft_model(model, lora_config)

        # LoRA 파인튜닝 수행
        model.train()
        optimizer = AdamW(model.parameters(), lr=5e-5)
        for epoch in range(3):
            total_loss = 0
            for text in training_data:
                inputs = tokenizer(text, return_tensors='pt', padding=True, truncation=True, max_length=512)

                # 'labels' 추가
                inputs = inputs.to(model.device)
                labels = inputs['input_ids'].clone()
                outputs = model(**inputs, labels=labels)

                # 손실 계산 및 역전파
                loss = outputs.loss
                loss.backward()
                optimizer.step()
                optimizer.zero_grad()

                total_loss += loss.item()
            print(f"Epoch {epoch+1} completed. Loss: {total_loss/len(training_data)}")

    # HuggingFacePipeline 객체 생성
    text_generation_pipeline = pipeline(
        model=model,
        tokenizer=tokenizer,
        task="text-generation",
        return_full_text=False,
        max_new_tokens=450,
    )

    hf = HuggingFacePipeline(pipeline=text_generation_pipeline)

    return hf, model, tokenizer


training_data = []

for _, row in df.iterrows():
    question = row['Question']
    answer = row['Answer']
    # 학습용 텍스트 생성
    text = f"질문: {question}\n답변: {answer}"
    training_data.append(text)


llm, model, tokenizer = setup_llm_pipeline(fine_tune=True, training_data=training_data)
