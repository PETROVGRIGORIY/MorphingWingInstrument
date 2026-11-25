import dafeaero as da

airfoil = da.Airfoil.from_file("task4_foils/E205.dat")
# airfoil.plot()
with_flap = airfoil.with_flap(30, 0.65)
with_flap.plot()


def generate_airfoil(a, b, c):
    # Создание профиля с параметрами a, b, c

a = (1, 5)
b = (0.2, 0.45)
c = (3, 4)
gene_space = (a, b, c)
da.optimization.launch_ga_optimization(generate_airfoil, gene_space)