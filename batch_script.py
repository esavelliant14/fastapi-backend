from app.services.juniper_collect import collect_interface, collect_policer

if __name__ == "__main__":
    print("=== Pilih mode ===")
    print("1. Ambil data interface")
    print("2. Ambil data firewall policer")
    mode = input("Mode: ")

    device_ip = input("Masukkan IP Router: ")

    if mode == "1":
        iface_name = input("Masukkan nama interface: ")
        collect_interface(device_ip, iface_name)

    elif mode == "2":
        collect_policer(device_ip)

    else:
        print("Mode tidak dikenal")

