import dafeaero as da

airfoil = da.Airfoil.from_file("task4_foils/E205.dat")
# airfoil.plot()
with_flap = airfoil.with_flap(30, 0.65)
with_flap.plot()
