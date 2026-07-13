"""Portas — as interfaces (Protocols) de tudo que é externo ao domínio.

CODEX: DIP / Dependency Inversion (Parte II) + Ports & Adapters.
    O domínio e os serviços dependem DESTAS abstrações, nunca de uma implementação
    concreta (um banco, um gateway de pagamento, um SMS). Trocar de fornecedor deve
    custar "1 adapter novo", não "refatorar metade do app".

CODEX: ISP / Interface Segregation (Parte II).
    Repare que são várias interfaces pequenas (`Notificador`, `Pagamento`, ...) em vez
    de uma `ServicosExternos` gorda. Ninguém é forçado a depender de método que não usa.
"""
