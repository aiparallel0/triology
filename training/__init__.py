"""Training drivers for the (init x lambda_struct) ablation grid.

S7 calls into a user-supplied `train_fn(adapter, config) -> dict` so
that the harness stays decoupled from any specific training stack.
This package ships one default callable for DONUT on SROIE; pass it
to S7 via TrainConfig.extra['train_fn']:

    from paper3.training.donut_sroie import train_donut_sroie
    cfg = TrainConfig(..., extra={'train_fn': train_donut_sroie,
                                   'sroie_root': '/data/SROIE_Task3'})
"""
