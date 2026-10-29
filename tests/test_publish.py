import publish


def _make_exe(path, content=b"binario-novo"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def test_publish_substitui_versao_anterior(tmp_path):
    source = _make_exe(tmp_path / "dist" / publish.EXE_NAME, b"versao-nova")
    destination = _make_exe(tmp_path / "Desktop" / publish.EXE_NAME, b"versao-antiga")

    status = publish.publish(source, destination, running=False)

    assert status == publish.STATUS_UPDATED
    assert destination.read_bytes() == b"versao-nova"


def test_publish_nao_faz_nada_se_versao_ja_e_igual(tmp_path):
    payload = b"mesmo-conteudo"
    source = _make_exe(tmp_path / "dist" / publish.EXE_NAME, payload)
    destination = _make_exe(tmp_path / "Desktop" / publish.EXE_NAME, payload)

    status = publish.publish(source, destination, running=False)

    assert status == publish.STATUS_UP_TO_DATE
    assert destination.read_bytes() == payload


def test_publish_aborta_com_executavel_em_execucao(tmp_path):
    source = _make_exe(tmp_path / "dist" / publish.EXE_NAME, b"novo")
    destination = _make_exe(tmp_path / "Desktop" / publish.EXE_NAME, b"antigo")

    status = publish.publish(source, destination, running=True)

    assert status == publish.STATUS_RUNNING
    assert destination.read_bytes() == b"antigo"


def test_publish_erro_quando_build_nao_existe(tmp_path):
    source = tmp_path / "dist" / publish.EXE_NAME
    destination = tmp_path / "Desktop" / publish.EXE_NAME

    status = publish.publish(source, destination, running=False)

    assert status == publish.STATUS_MISSING
    assert not destination.exists()


def test_publish_dry_run_nao_altera_nada(tmp_path):
    source = _make_exe(tmp_path / "dist" / publish.EXE_NAME, b"novo")
    destination = _make_exe(tmp_path / "Desktop" / publish.EXE_NAME, b"antigo")

    status = publish.publish(source, destination, dry_run=True, running=False)

    assert status == publish.STATUS_DRY_RUN
    assert destination.read_bytes() == b"antigo"


def test_publish_cria_destino_quando_nao_existe(tmp_path):
    source = _make_exe(tmp_path / "dist" / publish.EXE_NAME, b"primeira-versao")
    destination = tmp_path / "Desktop" / publish.EXE_NAME

    status = publish.publish(source, destination, running=False)

    assert status == publish.STATUS_UPDATED
    assert destination.read_bytes() == b"primeira-versao"


def test_desktop_dir_retorna_pasta_existente():
    assert publish.desktop_dir().is_dir()
