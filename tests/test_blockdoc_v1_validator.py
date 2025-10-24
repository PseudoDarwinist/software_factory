import json

from src.api.prd_editor import validate_block_document_v1


def test_blockdoc_v1_valid_minimal():
  payload = {
    "meta": {"title": "Test", "version": "v1"},
    "blocks": [
      {"type": "header", "content": {"level": 1, "text": "Title"}},
      {"type": "paragraph", "content": {"text": "Hello"}},
      {"type": "bullet-list", "content": {"items": ["a", "b"]}},
      {"type": "hr", "content": None},
    ],
  }
  doc = validate_block_document_v1(payload)
  assert isinstance(doc, dict)
  assert len(doc["blocks"]) == 4


def test_blockdoc_v1_rejects_bad_level():
  bad = {
    "blocks": [
      {"type": "header", "content": {"level": 42, "text": "oops"}}
    ]
  }
  try:
    validate_block_document_v1(bad)
    assert False, "should fail"
  except Exception:
    assert True


def test_blockdoc_v1_from_fenced_json():
  text = """```json
  {"blocks": [{"type":"paragraph","content":{"text":"Hi"}}]}
  ```"""
  doc = validate_block_document_v1(text)
  assert len(doc["blocks"]) == 1

