import importlib.util
import os

_p = os.path.join(os.path.dirname(__file__), "..", "chats.py")
_s = importlib.util.spec_from_file_location("ai_chats", _p)
C = importlib.util.module_from_spec(_s)
_s.loader.exec_module(C)


def test_roundtrip_filter_delete(tmp_path):
    st = C.ChatStore(str(tmp_path / "chats"))
    a = {"id": st.newId(), "title": "Editor: x", "project": "/p1",
         "messages": [{"role": "user", "content": "hi"},
                      {"role": "assistant", "agent": "Editor", "content": "yo"}]}
    b = {"id": st.newId(), "title": "Reader: y", "project": "/p2", "messages": []}
    st.save(a)
    st.save(b)
    assert st.load(a["id"])["messages"][1]["agent"] == "Editor"
    assert [c["id"] for c in st.list("/p1")] == [a["id"]]
    assert len(st.list()) == 2
    st.delete(a["id"])
    assert st.load(a["id"]) is None and len(st.list()) == 1


def test_title_and_corrupt_file(tmp_path):
    st = C.ChatStore(str(tmp_path))
    assert st.makeTitle("Reader", "a " * 40).startswith("Reader: a a")
    assert st.makeTitle("Reader", "").endswith("New chat")
    (tmp_path / "bad.json").write_text("{nope")
    assert st.list() == []
