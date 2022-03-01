import alqtendpy.compileui
import pathlib

def compile_ui():
    print("epyq::compile_ui building UI in epyq")
    alqtendpy.compileui.compile_ui(
        directory_paths=[pathlib.Path(__file__).parent / "src" / "epyq"],
    )

    print("epyq::compile_ui building UI in epyqlib")
    alqtendpy.compileui.compile_ui(
        directory_paths=[pathlib.Path(__file__).parent / "sub" / "epyqlib" / "epyqlib"],
    )
