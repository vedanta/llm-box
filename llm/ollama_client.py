from langchain_ollama import ChatOllama

llm = ChatOllama(model="llama3")

def ask_llm(filename: str, content: str = None) -> str:
    prompt = f"Summarize the purpose of files in the unix, mac or linux '{filename}' in one short line, ideally under 10 words."

    if content:
        prompt += f"\n\nHere is a sample of its content:\n{content[:500]}"

    try:
        response = llm.invoke(prompt)
        return response.content.strip()
    except Exception as e:
        return f"(LLM error: {str(e)})"
