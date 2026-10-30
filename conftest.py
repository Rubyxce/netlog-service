# 这个空文件的作用：告诉 pytest「项目的根目录在这里」
# pytest 会把 conftest.py 所在的目录加入 sys.path，
# 这样 tests/ 里的测试文件才能 import main
