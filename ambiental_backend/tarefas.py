# -*- coding: utf-8 -*-
"""Execucao em segundo plano com estado consultavel.

Simulacao e busca bibliografica podem levar minutos; a API responde 202 com o
`tarefa_id` e o frontend acompanha por `GET /api/tasks/{id}`. O estado fica no
banco (`amb_tarefas`), nao apenas na memoria: reinicio do Space nao apaga o
historico, e uma tarefa interrompida aparece como `interrompida` na leitura.
"""
from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor

from . import config
from . import persistencia as db
from .persistencia import Tarefa, json_dumps, json_loads, novo_id

_EXECUTOR = None
_TRAVA = threading.Lock()
ESTADOS_FINAIS = ("concluida", "falhou", "interrompida")


class TarefaNaoEncontrada(KeyError):
    """Identificador de tarefa inexistente."""


def executor() -> ThreadPoolExecutor:
    global _EXECUTOR
    with _TRAVA:
        if _EXECUTOR is None:
            _EXECUTOR = ThreadPoolExecutor(
                max_workers=config.max_tarefas(),
                thread_name_prefix="ambiental")
    return _EXECUTOR


def tarefa_dict(tarefa: Tarefa) -> dict:
    return {
        "id": tarefa.id,
        "pesquisa_id": tarefa.pesquisa_id,
        "tipo": tarefa.tipo,
        "estado": tarefa.estado,
        "progresso": tarefa.progresso,
        "mensagem": tarefa.mensagem,
        "resultado": json_loads(tarefa.resultado_json, None),
        "erro": tarefa.erro,
        "criada_em": (tarefa.criada_em.isoformat()
                      if tarefa.criada_em else None),
        "concluida_em": (tarefa.concluida_em.isoformat()
                         if tarefa.concluida_em else None),
    }


def _atualizar(tarefa_id: str, **campos) -> None:
    sessao_db = db.sessao()
    try:
        tarefa = sessao_db.get(Tarefa, tarefa_id)
        if tarefa is None:
            return
        for chave, valor in campos.items():
            if chave == "resultado":
                tarefa.resultado_json = json_dumps(valor)
            elif chave == "concluida":
                if valor:
                    tarefa.concluida_em = db._agora()
            else:
                setattr(tarefa, chave, valor)
        sessao_db.commit()
    finally:
        sessao_db.close()


def _executar(tarefa_id: str, funcao, args, kwargs) -> None:
    _atualizar(tarefa_id, estado="executando", progresso=10,
               mensagem="executando")
    try:
        resultado = funcao(*args, **kwargs)
    except Exception as erro:                       # noqa: BLE001
        _atualizar(tarefa_id, estado="falhou", progresso=100,
                   mensagem="falhou: %s" % type(erro).__name__,
                   erro="%s: %s" % (type(erro).__name__, erro),
                   concluida=True)
        return
    _atualizar(tarefa_id, estado="concluida", progresso=100,
               mensagem="concluida", resultado=resultado, concluida=True)


def registrar(pesquisa_id: str, tipo: str) -> dict:
    """Cria a linha da tarefa (estado `enfileirada`) sem executar nada.

    Separar `registrar` de `iniciar` permite gravar o `tarefa_id` na entidade
    (por exemplo, a simulacao) ANTES de o trabalho comecar — sem corrida entre
    o worker e a escrita do vinculo.
    """
    tarefa_id = novo_id("tar")
    sessao_db = db.sessao()
    try:
        sessao_db.add(Tarefa(id=tarefa_id, pesquisa_id=pesquisa_id, tipo=tipo,
                             estado="enfileirada", progresso=0,
                             mensagem="na fila"))
        sessao_db.commit()
    finally:
        sessao_db.close()
    return obter(tarefa_id)


def iniciar(tarefa_id: str, funcao, *args, **kwargs) -> dict:
    """Envia a tarefa registrada para o executor e devolve o estado atual."""
    executor().submit(_executar, tarefa_id, funcao, args, kwargs)
    return obter(tarefa_id)


def criar(pesquisa_id: str, tipo: str, funcao, *args, **kwargs) -> dict:
    """Atalho: registra e inicia em uma chamada."""
    tarefa = registrar(pesquisa_id, tipo)
    return iniciar(tarefa["id"], funcao, *args, **kwargs)


def obter(tarefa_id: str) -> dict:
    sessao_db = db.sessao()
    try:
        tarefa = sessao_db.get(Tarefa, str(tarefa_id).strip())
        if tarefa is None:
            raise TarefaNaoEncontrada("tarefa nao encontrada: %s" % tarefa_id)
        dados = tarefa_dict(tarefa)
        if dados["estado"] not in ESTADOS_FINAIS and dados["estado"] != "executando":
            dados["aviso"] = "tarefa pode ter sido interrompida por reinicio"
        return dados
    finally:
        sessao_db.close()


def listar(pesquisa_id: str = None, limite: int = 50) -> list:
    sessao_db = db.sessao()
    try:
        consulta = sessao_db.query(Tarefa)
        if pesquisa_id:
            consulta = consulta.filter(Tarefa.pesquisa_id == pesquisa_id)
        registros = (consulta.order_by(Tarefa.criada_em.desc())
                     .limit(max(1, min(int(limite), 200))).all())
        return [tarefa_dict(item) for item in registros]
    finally:
        sessao_db.close()


def aguardar(tarefa_id: str, timeout_s: float = 60.0,
             intervalo: float = 0.2) -> dict:
    """Espera a tarefa terminar (usado quando o cliente pede modo sincrono)."""
    limite = time.time() + max(1.0, float(timeout_s))
    while True:
        dados = obter(tarefa_id)
        if dados["estado"] in ESTADOS_FINAIS or time.time() >= limite:
            return dados
        time.sleep(intervalo)


def encerrar() -> None:
    global _EXECUTOR
    with _TRAVA:
        if _EXECUTOR is not None:
            _EXECUTOR.shutdown(wait=False, cancel_futures=True)
            _EXECUTOR = None
