#!/bin/bash
cd "$(dirname "$0")"
ROOT="$(pwd)"
cd Backend

if command -v python3 &>/dev/null; then
    PYCMD=python3
elif command -v python &>/dev/null; then
    PYCMD=python
else
    echo ""
    echo "Nem talalhato Python a gepen."
    echo "Toltsd le innen: https://www.python.org/downloads/"
    echo ""
    read -p "Nyomj Entert a kilepeshez..."
    exit 1
fi

echo "Fuggosegek ellenorzese / telepitese..."
if ! "$PYCMD" -m pip install -r "$ROOT/requirements.txt" --quiet; then
    echo ""
    echo "Hiba tortent a csomagok telepitese kozben."
    echo "Ellenorizd az internetkapcsolatot, majd probald ujra."
    read -p "Nyomj Entert a kilepeshez..."
    exit 1
fi

(
    sleep 2
    if command -v open &>/dev/null; then
        open http://localhost:5000
    elif command -v xdg-open &>/dev/null; then
        xdg-open http://localhost:5000
    fi
) &

echo "Jatekgyujtemeny inditasa ($PYCMD)..."
echo "Ha hiba van, a hibauzenet itt lathato lesz."
echo ""
"$PYCMD" app.py

echo ""
echo "A szerver leallt."
read -p "Nyomj Entert a kilepeshez..."
