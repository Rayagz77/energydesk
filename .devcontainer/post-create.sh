#!/usr/bin/env bash
# Outils complementaires installes a la creation du codespace.
set -euo pipefail

K9S_VERSION="${K9S_VERSION:-v0.50.6}"
K3D_INSTALL="${K3D_INSTALL:-true}"

echo ">>> k9s ${K9S_VERSION} (outil utilise en cours)"
curl -sSL -o /tmp/k9s.deb "https://github.com/derailed/k9s/releases/download/${K9S_VERSION}/k9s_linux_amd64.deb"
sudo apt-get install -y /tmp/k9s.deb
rm -f /tmp/k9s.deb

if [ "${K3D_INSTALL}" = "true" ]; then
  echo ">>> k3d (pour un cluster k3s, alternative a Minikube)"
  curl -sSL https://raw.githubusercontent.com/k3d-io/k3d/main/install.sh | bash
fi

echo ">>> Versions installees"
kubectl version --client || true
helm version || true
minikube version || true
terraform -version || true
k9s version --short || true
k3d version || true
pwsh -v || true
