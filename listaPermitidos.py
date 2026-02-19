class flabianos:
    """ Lista de admin """

    def __init__(self):
        self.Administradores=['eduardo']

    def TuSiTuNo(self,EllosSi):        
        if EllosSi in self.Adnubust:
            print('Bienvenido {}'.format(EllosSi))
        else:
            print('Lo siento {}, no estás en la lista de Adnubust.'.format(EllosSi))
