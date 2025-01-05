class SystemConfig:
    instrusion_state = ""

    @classmethod
    def set_intrusion(cls, val):
        cls.instrusion_state = val 
    
    @classmethod
    def get_intrusion(cls):
        return cls.instrusion_state