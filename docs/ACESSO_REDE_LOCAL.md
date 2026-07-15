# Acesso pela rede local

Este documento explica como abrir o Carteira Alpha 360 em celular ou outro computador da mesma rede.

## Arquivos principais

- `INICIAR_CARTEIRA_ALPHA_REDE.bat`: sobe backend e frontend e mostra as URLs atuais.
- `CONFIGURAR_ACESSO_REDE_ADMIN.bat`: libera o Firewall do Windows para acesso local.
- `DIAGNOSTICAR_ACESSO_REDE.bat`: gera diagnostico em `logs/carteira-alpha-lan-diagnostic.txt`.
- `logs/carteira-alpha-urls.txt`: lista as URLs atualizadas do dia.

## Como usar

1. No PC principal, execute `CONFIGURAR_ACESSO_REDE_ADMIN.bat` uma vez.
2. Execute `INICIAR_CARTEIRA_ALPHA_REDE.bat`.
3. No outro computador ou celular, abra a URL de IP exibida, por exemplo:

```text
http://192.168.0.102:5173
```

Tambem e possivel tentar:

```text
http://MICHEL-PCGAMER:5173
http://MICHEL-PCGAMER.local:5173
```

## Por que o IP muda

O roteador pode entregar um IP diferente para o PC a cada dia. Por isso o sistema sempre atualiza `logs/carteira-alpha-urls.txt`.

O acesso por `http://127.0.0.1:5173` funciona somente no proprio PC. Em outro computador, `127.0.0.1` aponta para o outro computador, nao para o PC principal.

## Firewall

O script de firewall cria duas regras:

- `Carteira Alpha 360 - Frontend LAN (5173)`
- `Carteira Alpha 360 - Backend LAN (8000)`

As regras aceitam apenas `LocalSubnet`, ou seja, dispositivos da rede local.

## Segundo roteador

Se a casa usa dois Wi-Fi/roteadores, pode existir isolamento de rede.

Exemplo:

- PC principal: `192.168.0.102`
- Celular/outro PC: `192.168.1.50`

Nesse caso os aparelhos parecem estar na mesma casa, mas estao em sub-redes diferentes. O Carteira Alpha 360 pode estar correto e ainda assim o acesso falhar.

Solucao recomendada:

- configurar o segundo roteador como Bridge/AP;
- desativar isolamento de clientes;
- ou criar rota/liberacao entre sub-redes.

## Diagnostico

Execute:

```powershell
.\scripts\check-lan-access.ps1 -OpenReport
```

O relatorio mostra:

- IPs atuais do PC;
- portas ouvindo em rede;
- regras do Firewall;
- testes HTTP locais;
- URLs para abrir em outros dispositivos;
- leitura provavel do bloqueio.
