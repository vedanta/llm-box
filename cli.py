import typer
from commands.llm_ls import llm_ls

def main(
    llm_ls_flag: bool = typer.Option(False, "--llm-ls", help="Use the LLM-enhanced ls"),
    path: str = typer.Argument(".", help="Path to scan")
):
    if llm_ls_flag:
        llm_ls(path)
    else:
        print("❌ Please pass --llm-ls to use the LLM file scanner.")

if __name__ == "__main__":
    typer.run(main)
