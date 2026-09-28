#!/usr/bin/env bash
# Inicializa el repo git local y deja todo listo para conectar con GitHub.
#
# Por qué este script y no lo hizo Claude directo: la carpeta que Cowork usa para
# este proyecto está montada en el sandbox de Claude con las eliminaciones de
# archivo bloqueadas (por diseño, para que el agente nunca pueda borrar algo tuyo
# sin que vos lo veas). Git necesita poder borrar archivos de lock internos para
# commitear, así que el "git init" tiene que correr acá, en tu Mac, no desde Cowork.
#
# Uso: desde esta carpeta, correr:  bash setup_repo.sh
set -euo pipefail
cd "$(dirname "$0")"

if [ -d .git ]; then
  echo "Ya existe una carpeta .git (puede ser un intento previo fallido desde Cowork)."
  read -p "¿Borrarla y reinicializar limpio? [y/N] " ans
  if [[ "$ans" == "y" || "$ans" == "Y" ]]; then
    rm -rf .git
  else
    echo "Cancelado. Revisá el estado de .git manualmente antes de continuar."
    exit 1
  fi
fi

git init
git add -A
git commit -m "Initial scaffold: Savings Engine plugin (contract-ingest, discount-finder, savings-report, discount-email)

- 4 skills covering the pipeline: ingest contracts -> detect discount levers -> HTML report -> Outlook draft (HITL)
- v0 draft schemas (contract summary JSON, discount levers taxonomy) pending real examples
- config/ and output/ gitignored (no client data versioned)"

git branch -M main

echo ""
echo "Listo. Commit inicial hecho en la rama 'main'."
echo ""
echo "Para conectarlo a GitHub:"
echo "  1) Creá un repo vacío (sin README/gitignore) en https://github.com/new"
echo "  2) git remote add origin <URL_DEL_REPO_QUE_CREASTE>"
echo "  3) git push -u origin main"
