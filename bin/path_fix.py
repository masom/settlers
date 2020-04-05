import pathlib
import sys

work_dir = pathlib.Path(__file__).resolve().parent.parent
src_path = work_dir / 'src'

sys.path.append(str(src_path))
