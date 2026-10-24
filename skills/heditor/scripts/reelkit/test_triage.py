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


def words(text, t0=0.0, step=0.3, p=0.95):
    return [{"word": w, "start": round(t0 + i * step, 2), "end": round(t0 + i * step + 0.25, 2), "p": p}
            for i, w in enumerate(text.split())]


def test_aside_intents_and_instructions():
    assert tr.aside_intent("Foi errado esse aí. Corta aí, editor.") == "cut"
    assert tr.aside_intent("Não, de novo. Agora não.") == "redo"
    assert tr.aside_intent("Não, vamos editar essa parte, essa última frase.") == "note"
    assert tr.aside_intent("Atenção!") == "marker"
    assert tr.aside_intent("Let me redo that", "en") == "redo"
    rows = tr.classify([chunk(0, 3, "que é o documento com tudo que o sistema precisa."),
                        chunk(4, 6, "Não, vamos editar essa parte, essa última frase."),
                        chunk(7, 10, "que é o documento com tudo o que o sistema precisa fazer.")])
    ins = tr.instructions(rows)
    assert len(ins) == 1 and ins[0]["intent"] == "note"
    assert ins[0]["before"]["chunk"] == 0 and ins[0]["after"]["chunk"] == 2


def test_issues_inside_a_usable_chunk():
    c = {"a": 0, "b": 6, "text": "", "label": "keep"}
    c["words"] = words("Eu comparo com com o PRD antes de seguir")
    assert [x["kind"] for x in tr.chunk_issues(c)] == ["stutter"]
    c["words"] = words("Primeiro, uma instância conectada por trás, não, conectada ao sistema")
    assert "self_correction" in [x["kind"] for x in tr.chunk_issues(c)]
    c["words"] = words("o login funciona e aí corta isso editor e o banco de dados")
    kinds = [x["kind"] for x in tr.chunk_issues(c)]
    assert "aside_inside" in kinds
    c["words"] = words("com acesso a todos os cursos da escola")
    hit = [x for x in tr.chunk_issues(c, forbid=["todos os cursos"]) if x["kind"] == "forbidden"]
    assert hit and hit[0]["text"] == "todos os cursos" and hit[0]["start"] == 0.9
    c["words"] = words("um sistema completo") + [{"word": "integradíssimo", "start": 1.0, "end": 1.4, "p": 0.2}]
    assert [x["kind"] for x in tr.chunk_issues(c)] == ["unclear"]
    c["words"] = words("Não, isso não é bem assim, não é o que eu disse")   # plain negations are not corrections
    assert tr.chunk_issues(c) == []


def test_tech_report_finds_clipping_a_knock_and_a_light_change(tmp_path):
    import subprocess
    sr = 48000
    t = np.arange(4 * sr) / sr
    x = np.zeros_like(t)
    for a, b in ((0.5, 1.5), (2.5, 3.5)):
        m = (t >= a) & (t < b)
        x[m] = 0.3 * np.sin(2 * np.pi * 220 * t[m])
    x[int(1.0 * sr): int(1.0 * sr) + 40] = 1.0          # clipped run inside speech
    x[int(2.0 * sr): int(2.0 * sr) + 400] = 0.5          # a knock between the sentences
    wav = tmp_path / "a.wav"
    import wave
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype("<i2").tobytes())
    vid = tmp_path / "v.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=0x404040:s=108x192:r=30:d=2",
                    "-f", "lavfi", "-i", "color=c=0xa0a0a0:s=108x192:r=30:d=2", "-i", str(wav), "-filter_complex",
                    "[0:v][1:v]concat=n=2:v=1:a=0[v]", "-map", "[v]", "-map", "2:a", "-c:v", "libx264", "-pix_fmt",
                    "yuv420p", "-c:a", "aac", str(vid)], check=True)
    rows = [dict(chunk(0.5, 1.5, "primeira frase do vídeo"), label="keep"),
            dict(chunk(2.5, 3.5, "segunda frase do vídeo"), label="keep")]
    rep = tr.tech_report(vid, rows)
    assert rep["clipping"]["events"] >= 1 and abs(rep["clipping"]["times"][0] - 1.0) < 0.05
    assert any(abs(s["t"] - 2.0) < 0.05 for s in rep["sounds_outside_speech"])
    assert rep["picture_jumps_between_kept"] and rep["picture_jumps_between_kept"][0]["why"] == "light changed"
