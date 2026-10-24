"""Unit tests for raw-take triage and notation folding (no models): chunking, labels, asr-check normalisation."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import triage as tr  # noqa: E402
from textnorm import notation_tokens, same_notation  # noqa: E402


def chunk(a, b, text, p=0.95):
    return {"a": a, "b": b, "text": text, "words": [{"word": w, "p": p} for w in text.split()]}


def test_notation_folding_is_only_notation():
    assert same_notation("para a próxima", "pra próxima")
    assert same_notation("às 7 e meia da noite", "às 7h30 da noite")
    assert same_notation("cinco passos", "5 passos")
    assert same_notation("IA Builders", "IABuilders")
    assert same_notation("Fast API", "FastAPI")
    assert not same_notation("ia", "iam")
    assert not same_notation("a que", "ack")
    assert notation_tokens("19:30", "pt") == ["19", "30"]


def test_voiced_chunks_merges_short_gaps_and_splits_reading_pauses():
    db = np.full(600, -80.0)
    db[50:150] = -20       # 0.5-1.5 s
    db[170:250] = -20      # 0.2 s gap -> same chunk
    db[400:500] = -20      # 1.5 s reading pause -> new chunk
    db[560:563] = -20      # 30 ms click -> dropped (min_len)
    assert tr.voiced_chunks(db) == [[0.5, 2.5], [4.0, 5.0]]


def test_aside_to_the_editor_and_the_rejected_take():
    rows = tr.classify([
        chunk(4.4, 7.7, "Essa resposta do WhatsApp foi escrita por um chatbot de IA."),
        chunk(31.9, 34.9, "Primeiro, uma instância do WhatsApp conectada por trás dele."),
        chunk(37.5, 37.7, "Não."),
        chunk(38.7, 41.3, "Foi errado esse aí. Corta aí, editor."),
        chunk(44.1, 46.8, "Primeiro, uma instância do WhatsApp conectada ao sistema."),
    ])
    assert [r["label"] for r in rows] == ["keep", "retake", "noise", "editor", "keep"]
    assert "confirm" in rows[4]["note"]


def test_restart_chain_with_editor_cues():
    rows = tr.classify([
        chunk(22.4, 25.5, "Os dois primeiros são o Prompt Bruto e o PRD."),
        chunk(29.5, 32.0, "que é o documento com tudo que o sistema precisa."),
        chunk(35.1, 37.7, "Não, vamos editar essa parte, essa última frase."),
        chunk(40.2, 42.8, "que é o documento com tudo o que o sistema precisa fazer."),
        chunk(48.5, 49.7, "O próximo passo..."),
        chunk(50.1, 51.4, "Não, de novo. Agora não."),
        chunk(56.1, 56.8, "Editor."),
        chunk(57.8, 58.7, "Vamos de novo."),
        chunk(67.6, 72.3, "O terceiro passo é preparar a base do projeto, o que eu chamo de Start Template."),
    ])
    assert [r["label"] for r in rows] == ["keep", "retake", "editor", "keep", "retake", "editor", "editor", "editor",
                                          "keep"]


def test_false_start_and_no_false_alarm_inside_speech():
    rows = tr.classify([
        chunk(48.9, 50.2, "No Integration Master,"),
        chunk(52.6, 53.4, "Você começa..."),
        chunk(55.3, 57.5, "Você conecta esse sistema a APIs"),
        chunk(60.0, 62.0, "a Webhooks e a API do WhatsApp."),
        chunk(70.0, 73.0, "Código da IA que não roda? Antes de abrir o editor, eu escrevo."),
    ])
    assert [r["label"] for r in rows] == ["keep", "false_start", "keep", "keep", "keep"]


def test_hallucination_on_a_noise_chunk():
    rows = tr.classify([chunk(0.05, 0.33, "Legendas pela comunidade Amara.org"),
                        chunk(0.65, 5.4, "As próximas etapas eu mostro na aula do dia 5.")])
    assert [r["label"] for r in rows] == ["noise", "keep"]


def test_english_cues():
    rows = tr.classify([chunk(0, 3, "This is the first version of the line"), chunk(4, 5, "Let me redo that."),
                        chunk(6, 9, "This is the second version of the line")], lang="en")
    assert [r["label"] for r in rows] == ["retake", "editor", "keep"]
