# Uninstallation

If you decide to remove Needle from your system, you can do so quickly by running the following one-liner command in your terminal:

```bash
curl -fsSL https://raw.githubusercontent.com/UIC-InDeXLab/Needle/main/scripts/uninstall.sh | bash
```

> **Note:** This uninstallation command will remove Needle's services, data and configurations. However, it will not remove any cached Docker images. If you need to free up additional disk space, please consider manually removing those images.