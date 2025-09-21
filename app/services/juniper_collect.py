import os
from jnpr.junos import Device
from lxml import etree
from dotenv import load_dotenv
from app.db.db_utils import get_connection

# load env kalau belum
load_dotenv()

JUNIPER_USER = os.getenv("JUNIPER_USER")
JUNIPER_PASS = os.getenv("JUNIPER_PASS")


def collect_interface(device_ip: str, mode: str, hostnameku: str, iface_name: str  ):
    """
    Login ke Junos via NETCONF dan menampilkan informasi interface.
    """

    dev = Device(host=device_ip, user=JUNIPER_USER, passwd=JUNIPER_PASS)
    
    if mode == "1":
        dev.open()
        filter_xml = etree.XML(f'''
        <configuration>
          <interfaces>
            <interface>
              <name>{iface_name}</name>
            </interface>
          </interfaces>
        </configuration>
        ''')

        cfg = dev.rpc.get_config(filter_xml=filter_xml)

        # Parsing data
        interface_name = cfg.findtext('.//interface/name')
        data_to_insert = []


        for unit in cfg.xpath('.//unit'):
            unit_name = unit.findtext('name')
            attr_unit = unit.get('inactive')
            if attr_unit:
                status_unit_1 = "Inactive"
            else:
                status_unit_1 = "Active"

            #check disable atau tidak
            if unit.find('disable') is not None:
                status_unit_2 = "Disable"
            else:
                status_unit_2 = "Enable"

            status_unit = f"{status_unit_1} | {status_unit_2}"
            #ip_list = [addr.text for addr in unit.xpath('family/inet/address/name')]
            #ip = ", ".join(ip_list) if ip_list else "None"
            ip_list = []
            for addr_el in unit.xpath('family/inet/address'):
                ip_addr = addr_el.findtext('name')
                inactive_attr = addr_el.get('inactive')
                if inactive_attr:  # ada attribute inactive
                    ip_list.append(f"{ip_addr}(inactive)")
                else:
                    ip_list.append(ip_addr)
            ip = ", ".join(ip_list) if ip_list else "None"
            #description
            description = unit.findtext('description')
            #status policer
            find_status_policer = unit.find('.//family/inet/policer')
            if find_status_policer is None:
                status_policer = "None"
            else:
                attr_policer = find_status_policer.get('inactive')
                if attr_policer:
                    status_policer = "Inactive"
                else:
                    status_policer = "Active"

            #status policer input
            find_status_input_policer = unit.find('.//family/inet/policer/input')
            if find_status_input_policer is None:
                status_input_policer = "None"
            else:
                attr_input_policer = find_status_input_policer.get('inactive')
                if attr_input_policer:
                    status_input_policer = "Inactive"
                else:
                    status_input_policer = "Active"
            #status policer output
            find_status_output_policer = unit.find('.//family/inet/policer/output')
            if find_status_output_policer is None:
                status_output_policer = "None"
            else:
                attr_output_policer = find_status_output_policer.get('inactive')
                if attr_output_policer:
                    status_output_policer = "Inactive"
                else:
                    status_output_policer = "Active"
            #value policer input & output
            raw_input_policer = unit.findtext('family/inet/policer/input')
            input_policer = raw_input_policer if raw_input_policer else "None"
            raw_output_policer = unit.findtext('family/inet/policer/output')
            output_policer = raw_output_policer if raw_output_policer else "None"
            vlan_id = unit.findtext('vlan-id')
            

            print(f"Hostname: {hostnameku}" )
            print(f"Interface: {interface_name}")
            print(f"Unit: {unit_name}")
            print(f"Status Unit: {status_unit}")
            print(f"Description: {description}")
            print(f"IP Address: {ip}")
            print(f"VLAN ID: {vlan_id}")
            print(f"Policer status: {status_policer}")
            print(f"Policer Input status: {status_input_policer}")
            print(f"Policer Output status: {status_output_policer}")
            print(f"Input policer: {input_policer}")
            print(f"Output policer: {output_policer}\n")

            data_to_insert.append((
                hostnameku,
                interface_name,
                unit_name,
                status_unit,
                description,
                ip,
                vlan_id,
                status_policer,
                input_policer,
                status_input_policer,
                output_policer,
                status_output_policer,


            ))

        dev.close()

        save_db = input("Save to database? (y/n): ")

        if save_db.lower() == 'y':
            # koneksi ke MySQL
            conn = get_connection()
            cursor = conn.cursor()

            # pastikan tabel sudah ada: misal table_client
            sql = """INSERT INTO table_bwm_client
                     (hostname, interface, unit_interface, status_unit, description, ip_address, vlan_id, policer_status,
                     input_policer, input_policer_status, output_policer, output_policer_status, id_group, id_user)
                     VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, "2", "2")"""

            cursor.executemany(sql, data_to_insert)
            conn.commit()
            cursor.close()
            conn.close()
            print("Data berhasil disimpan ke database.")
        else:
            print("End session. Tidak disimpan ke database.")

    else:
        dev.open()
        filter_xml = etree.XML(f'''
        <configuration>
        <logical-systems>
          <name>{hostnameku}</name>
          <interfaces>
            <interface>
              <name>{iface_name}</name>
            </interface>
          </interfaces>
        </logical-systems>
        </configuration>
        ''')

        cfg = dev.rpc.get_config(filter_xml=filter_xml)

        # Parsing data
        interface_name = cfg.findtext('.//interface/name')
        data_to_insert = []


        for unit in cfg.xpath('.//unit'):
            unit_name = unit.findtext('name')
            attr_unit = unit.get('inactive')
            if attr_unit:
                status_unit_1 = "Inactive"
            else:
                status_unit_1 = "Active"

            #check disable atau tidak
            if unit.find('disable') is not None:
                status_unit_2 = "Disable"
            else:
                status_unit_2 = "Enable"

            status_unit = f"{status_unit_1} | {status_unit_2}"
            #ip_list = [addr.text for addr in unit.xpath('family/inet/address/name')]
            #ip = ", ".join(ip_list) if ip_list else "None"
            ip_list = []
            for addr_el in unit.xpath('family/inet/address'):
                ip_addr = addr_el.findtext('name')
                inactive_attr = addr_el.get('inactive')
                if inactive_attr:  # ada attribute inactive
                    ip_list.append(f"{ip_addr}(inactive)")
                else:
                    ip_list.append(ip_addr)
            ip = ", ".join(ip_list) if ip_list else "None"
            #description
            description = unit.findtext('description')
            #status policer
            find_status_policer = unit.find('.//family/inet/policer')
            if find_status_policer is None:
                status_policer = "None"
            else:
                attr_policer = find_status_policer.get('inactive')
                if attr_policer:
                    status_policer = "Inactive"
                else:
                    status_policer = "Active"

            #status policer input
            find_status_input_policer = unit.find('.//family/inet/policer/input')
            if find_status_input_policer is None:
                status_input_policer = "None"
            else:
                attr_input_policer = find_status_input_policer.get('inactive')
                if attr_input_policer:
                    status_input_policer = "Inactive"
                else:
                    status_input_policer = "Active"
            #status policer output
            find_status_output_policer = unit.find('.//family/inet/policer/output')
            if find_status_output_policer is None:
                status_output_policer = "None"
            else:
                attr_output_policer = find_status_output_policer.get('inactive')
                if attr_output_policer:
                    status_output_policer = "Inactive"
                else:
                    status_output_policer = "Active"
            #value policer input & output
            raw_input_policer = unit.findtext('family/inet/policer/input')
            input_policer = raw_input_policer if raw_input_policer else "None"
            raw_output_policer = unit.findtext('family/inet/policer/output')
            output_policer = raw_output_policer if raw_output_policer else "None"
            vlan_id = unit.findtext('vlan-id')
            

            print(f"Hostname: {hostnameku}" )
            print(f"Interface: {interface_name}")
            print(f"Unit: {unit_name}")
            print(f"Status Unit: {status_unit}")
            print(f"Description: {description}")
            print(f"IP Address: {ip}")
            print(f"VLAN ID: {vlan_id}")
            print(f"Policer status: {status_policer}")
            print(f"Policer Input status: {status_input_policer}")
            print(f"Policer Output status: {status_output_policer}")
            print(f"Input policer: {input_policer}")
            print(f"Output policer: {output_policer}\n")

            data_to_insert.append((
                hostnameku,
                interface_name,
                unit_name,
                status_unit,
                description,
                ip,
                vlan_id,
                status_policer,
                input_policer,
                status_input_policer,
                output_policer,
                status_output_policer,


            ))

        dev.close()

        save_db = input("Save to database? (y/n): ")

        if save_db.lower() == 'y':
            # koneksi ke MySQL
            conn = get_connection()
            cursor = conn.cursor()

            # pastikan tabel sudah ada: misal table_client
            sql = """INSERT INTO table_bwm_client
                     (hostname, interface, unit_interface, status_unit, description, ip_address, vlan_id, policer_status,
                     input_policer, input_policer_status, output_policer, output_policer_status, id_group, id_user)
                     VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, "2", "2")"""

            cursor.executemany(sql, data_to_insert)
            conn.commit()
            cursor.close()
            conn.close()
            print("Data berhasil disimpan ke database.")
        else:
            print("End session. Tidak disimpan ke database.")


def collect_policer(device_ip: str, mode: str, hostnameku: str):

    """
    Login ke Junos via NETCONF dan menampilkan informasi interface.
    """
    dev = Device(host=device_ip, user=JUNIPER_USER, passwd=JUNIPER_PASS)
    if mode == "1":
        dev.open()
        filter_xml = etree.XML("""
        <configuration>
          <firewall>
            <policer/>
          </firewall>
        </configuration>
        """)
        cfg = dev.rpc.get_config(filter_xml=filter_xml)

        data_to_insert = []

        for policer in cfg.xpath('.//policer'):
            name = policer.findtext('name')
            attr_bw = policer.get('inactive')
            if attr_bw:
                status_bw = "Inactive"
            else:
                status_bw = "Active"
            if not name:
                continue
            if policer.find('if-exceeding') is not None:
                bandwidth = policer.findtext('if-exceeding/bandwidth-limit')
                burst = policer.findtext('if-exceeding/burst-size-limit')
            else:
                bandwidth = burst = None

            print(f"Hostname: {hostnameku}")
            print(f"Policer: {name}")
            print(f"Status policer: {status_bw}")
            print(f"Bandwidth: {bandwidth}")
            print(f"burst: {burst}\n")
            data_to_insert.append((
                hostnameku,
                name, 
                bandwidth, 
                burst,
                status_bw,
            ))

        dev.close()


        save_db = input("Save to database? (y/n): ")

        if save_db.lower() == 'y':
            # koneksi ke MySQL
            conn = get_connection()
            cursor = conn.cursor()

            # pastikan tabel sudah ada: misal table_bwm_bw
            sql = """INSERT INTO table_bwm_bw
                     (hostname, policer_name, bandwidth, burst_limit, policer_status, id_group, id_user)
                     VALUES (%s, %s, %s, %s, %s, "2", "2")"""

            cursor.executemany(sql, data_to_insert)
            conn.commit()
            cursor.close()
            conn.close()
            print("Data berhasil disimpan ke database.")
        else:
            print("End session. Tidak disimpan ke database.")

    else:

        dev.open()
        filter_xml = etree.XML(f'''
        <configuration>
        <logical-systems>
          <name>{hostnameku}</name>
          <firewall>
            <policer/>
          </firewall>
        </logical-systems>
        </configuration>
        ''')
        cfg = dev.rpc.get_config(filter_xml=filter_xml)

        data_to_insert = []

        for policer in cfg.xpath('.//policer'):
            name = policer.findtext('name')
            attr_bw = policer.get('inactive')
            if attr_bw:
                status_bw = "Inactive"
            else:
                status_bw = "Active"
            if not name:
                continue
            if policer.find('if-exceeding') is not None:
                bandwidth = policer.findtext('if-exceeding/bandwidth-limit')
                burst = policer.findtext('if-exceeding/burst-size-limit')
            else:
                bandwidth = burst = None

            print(f"Hostname: {hostnameku}")
            print(f"Policer: {name}")
            print(f"Status policer: {status_bw}")
            print(f"Bandwidth: {bandwidth}")
            print(f"burst: {burst}\n")
            data_to_insert.append((
                hostnameku,
                name, 
                bandwidth, 
                burst,
                status_bw,
            ))

        dev.close()


        save_db = input("Save to database? (y/n): ")

        if save_db.lower() == 'y':
            # koneksi ke MySQL
            conn = get_connection()
            cursor = conn.cursor()

            # pastikan tabel sudah ada: misal table_bwm_bw
            sql = """INSERT INTO table_bwm_bw
                     (hostname, policer_name, bandwidth, burst_limit, policer_status, id_group, id_user)
                     VALUES (%s, %s, %s, %s, %s, "2", "2")"""

            cursor.executemany(sql, data_to_insert)
            conn.commit()
            cursor.close()
            conn.close()
            print("Data berhasil disimpan ke database.")
        else:
            print("End session. Tidak disimpan ke database.")
