#!/bin/bash

# ----------------------------------
# Script inteligente de inicialização
# ----------------------------------

# Caminho do ambiente virtual
VENV_PATH=~/meu_app/api/venv/bin/activate

# Caminho da API
API_PATH=~/meu_app/api/api_termux_final_cell.py

# Porta que a API usa
PORT=8000

# Função para checar se a porta está ocupada
is_port_in_use() {
    lsof -i :$PORT >/dev/null 2>&1
    return $?
}

# Se a porta não estiver em uso, inicia a API
if ! is_port_in_use; then
    echo "API não está rodando. Iniciando..."
    # Ativa wake-lock
    termux-wake-lock
    # Ativa o ambiente virtual
    source $VENV_PATH
    # Inicia a API em segundo plano
    nohup python $API_PATH > api.log 2>&1 &
    echo "API iniciada em segundo plano!"
else
    echo "API já está rodando na porta $PORT!"
fi
