# cli.py

import typer
from commands.llm_ls import llm_ls
from commands.llm_cat import llm_cat

def main(
    llm_ls_flag: bool = typer.Option(False, "--llm-ls", help="List files with LLM explanations"),
    llm_cat_flag: bool = typer.Option(False, "--llm-cat", help="Summarize a file using an LLM"),
    path: str = typer.Argument(..., help="Path to scan (for ls) or file to summarize (for cat)")
):
    if llm_ls_flag:
        llm_ls(path)
    elif llm_cat_flag:
        llm_cat(path)
    else:
        print("❌ Please specify a valid command flag like --llm-ls or --llm-cat")

if __name__ == "__main__":
    typer.run(main)
