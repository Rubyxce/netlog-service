import os

# 让测试用固定的 API_KEY，不受开发机环境影响。
# 必须在 import main 之前执行 —— conftest.py 是 pytest 最先加载的文件。
os.environ.setdefault("API_KEY", "test-key")

# 告诉 pytest「项目的根目录在这里」：
# pytest 会把 conftest.py 所在的目录加入 sys.path，
# 这样 tests/ 里的测试文件才能 import main
