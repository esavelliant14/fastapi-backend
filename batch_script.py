from app.services.juniper_collect import collect_interface, collect_policer

if __name__ == "__main__":
    print("=== Pilih mode ===")
    print("1. Ambil data interface")
    print("2. Ambil data firewall policer")
    getconf = input("Config: ")

    device_ip = input("Masukkan IP Router: ")

    print("1. Normal System")
    print("2. Logical System")
    mode = input("Mode: ")

    hostnameku = input("Masukkan hostname: ")


    if getconf == "1":
        iface_name = input("Masukkan nama interface: ")
        collect_interface(device_ip, mode, hostnameku ,iface_name)

    elif getconf == "2":
        collect_policer(device_ip, mode, hostnameku)

    else:
        print("Mode tidak dikenal")

