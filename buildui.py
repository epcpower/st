import alqtendpy.compileui
import pathlib

# import epyqlib.buildui


def compile_ui():
    print("epyq::compile_ui building UI in epyq")
    alqtendpy.compileui.compile_ui(
        directory_paths=[pathlib.Path(__file__).parent / "src" / "epyq"],
    )

    # todo, both of these are the same.  change it only have one
    alqtendpy.compileui.compile_ui(
        directory_paths=[pathlib.Path(__file__).parent / "sub" / "epyqlib" / "epyqlib"],
    )


#    epyqlib.buildui.compile_ui()
