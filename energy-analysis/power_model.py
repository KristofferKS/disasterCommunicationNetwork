class PowerModel:
    def __init__(self, lambda_m, M, N, tech, C_bat):
        self.lambda_m = self.lambda_m_base = lambda_m
        self.M = self.M_base = M
        self.N = self.N_base = N
        self.C_bat = self.C_bat_base = C_bat
        self.tech = tech

    def return_to_base(self):
        self.lambda_m = self.lambda_m_base
        self.M = self.M_base
        self.N = self.N_base
        self.C_bat = self.C_bat_base

    def delta_Tx(self, tech_params):
        return self.lambda_m * self.M / (tech_params["eta"] * tech_params["R_raw"])
    
    def delta_Rx(self, tech_params):
        return (self.N - 1) * self.lambda_m * self.M / (tech_params["eta"] * tech_params["R_raw"])
    
    def delta_idle(self, tech_params):
        return 1 - self.delta_Tx(tech_params) - self.delta_Rx(tech_params)

    def power_model(self, tech_params):
        d_tx   = self.delta_Tx(tech_params)
        d_rx   = self.delta_Rx(tech_params)
        d_idle = self.delta_idle(tech_params)

        if d_tx + d_rx >= 1:
            return None

        I_bar  = (tech_params["I_base"]
                + d_idle * tech_params["I_idle"]
                + d_tx   * tech_params["I_tx"]
                + d_rx   * tech_params["I_rx"])

        T_life = self.C_bat / I_bar                                     # hours

        return dict(d_tx=d_tx, d_rx=d_rx, d_idle=d_idle,
                    I_bar=I_bar, T_life=T_life)