# app/main.py
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine, text
from pydantic import BaseModel
from jnpr.junos import Device
from jnpr.junos.utils.config import Config
from lxml import etree
from datetime import datetime
import os, threading
from dotenv import load_dotenv
from jnpr.junos.exception import ConnectError, ConnectRefusedError, ConnectAuthError, RpcTimeoutError


load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_NAME = os.getenv("DB_NAME")
JUNIPER_USER = os.getenv("JUNIPER_USER")
JUNIPER_PASS = os.getenv("JUNIPER_PASS")


DB_URL = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}"
engine = create_engine(DB_URL)

app = FastAPI()

# === Tambahan mekanisme LOCK ===
device_locks = {}

def get_device_lock(hostname: str):
    """Dapatkan lock untuk hostname tertentu."""
    if hostname not in device_locks:
        device_locks[hostname] = threading.Lock()
    return device_locks[hostname]
# ===============================

# model request yang masuk dari Laravel
class ClientData(BaseModel):
    hostname: str
    interface: str
    unit: int



@app.post("/receive-client")
def receive_client(data: ClientData):
    # login ke device
    try:
        with engine.begin() as conn:
            router = conn.execute(
                text("SELECT ip_address, logical_system FROM table_bwm_rtr WHERE hostname=:h LIMIT 1"),
                {"h": data.hostname}
            ).fetchone()

        ip_device = router.ip_address
        logical_system = router.logical_system

        with Device(host=ip_device, user=JUNIPER_USER, passwd=JUNIPER_PASS, timeout=10) as dev:

            if logical_system == "no":
            # filter config untuk interface spesifik
                filter_xml = etree.XML(f'''
                <configuration>
                  <interfaces>
                    <interface>
                      <name>{data.interface}</name>
                      <unit>
                        <name>{data.unit}</name>
                      </unit>
                    </interface>
                  </interfaces>
                </configuration>
                ''')

                cfg = dev.rpc.get_config(filter_xml=filter_xml)

                # cek unit ada?
                unit_names = [unit.findtext('name') for unit in cfg.xpath('.//unit')]
                if str(data.unit) not in unit_names:
                    # return {
                    #     "status": "failed",
                    #     "message": f"Unit {data.unit} was not found on interface {data.interface} at device {data.hostname}"
                    # }
                    return JSONResponse(
                        status_code=404,
                        content={
                            "status":"failed",
                            "message":f"Unit {data.unit} was not found on interface {data.interface} at {data.hostname}",
                        }
                    )

                else:
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
                        
                    #     #status policer
                        find_status_policer = unit.find('.//family/inet/policer')
                        if find_status_policer is None:
                            status_policer = "None"
                        else:
                            attr_policer = find_status_policer.get('inactive')
                            if attr_policer:
                                status_policer = "Inactive"
                            else:
                                status_policer = "Active"

                    #     #status policer input
                        find_status_input_policer = unit.find('.//family/inet/policer/input')
                        if find_status_input_policer is None:
                            status_input_policer = "None"
                        else:
                            attr_input_policer = find_status_input_policer.get('inactive')
                            if attr_input_policer:
                                status_input_policer = "Inactive"
                            else:
                                status_input_policer = "Active"

                    #    #status policer output
                        find_status_output_policer = unit.find('.//family/inet/policer/output')
                        if find_status_output_policer is None:
                            status_output_policer = "None"
                        else:
                            attr_output_policer = find_status_output_policer.get('inactive')
                            if attr_output_policer:
                                status_output_policer = "Inactive"
                            else:
                                status_output_policer = "Active"

                    #     #value policer input & output
                        raw_input_policer = unit.findtext('family/inet/policer/input')
                        input_policer = raw_input_policer if raw_input_policer else "None"
                        raw_output_policer = unit.findtext('family/inet/policer/output')
                        output_policer = raw_output_policer if raw_output_policer else "None"
                        
                    #     #vlan_id
                        vlan_id = unit.findtext('vlan-id')

                    # jika semua ada
                    return {
                        "status": "success",
                        "message": f"Interface {data.interface} unit {data.unit} found at device {data.hostname}. success to add",
                        "hostname": data.hostname,
                        "interface": data.interface,
                        "unit": unit_name,
                        "status_unit": status_unit,
                        "description": description,
                        "ip": ip,
                        "vlan_id": vlan_id,
                        "status_policer": status_policer,
                        "status_input_policer": status_input_policer,
                        "status_output_policer": status_output_policer,
                        "input_policer": input_policer,
                        "output_policer": output_policer,
                    }
            else:
                filter_xml = etree.XML(f'''
                <configuration>
                    <logical-systems>
                        <name>{data.hostname}</name>
                        <interfaces>
                            <interface>
                              <name>{data.interface}</name>
                                <unit>
                                    <name>{data.unit}</name>
                                </unit>
                            </interface>
                      </interfaces>
                    </logical-systems>
                </configuration>
                ''')

                cfg = dev.rpc.get_config(filter_xml=filter_xml)

                # cek unit ada?
                unit_names = [unit.findtext('name') for unit in cfg.xpath('.//unit')]
                if str(data.unit) not in unit_names:
                    # return {
                    #     "status": "failed",
                    #     "message": f"Unit {data.unit} was not found on interface {data.interface} at device {data.hostname}"
                    # }
                    return JSONResponse(
                        status_code=404,
                        content={
                            "status":"failed",
                            "message":f"Unit {data.unit} was not found on interface {data.interface} at {data.hostname}",
                        }
                    )

                else:
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
                        
                    #     #status policer
                        find_status_policer = unit.find('.//family/inet/policer')
                        if find_status_policer is None:
                            status_policer = "None"
                        else:
                            attr_policer = find_status_policer.get('inactive')
                            if attr_policer:
                                status_policer = "Inactive"
                            else:
                                status_policer = "Active"

                    #     #status policer input
                        find_status_input_policer = unit.find('.//family/inet/policer/input')
                        if find_status_input_policer is None:
                            status_input_policer = "None"
                        else:
                            attr_input_policer = find_status_input_policer.get('inactive')
                            if attr_input_policer:
                                status_input_policer = "Inactive"
                            else:
                                status_input_policer = "Active"

                    #    #status policer output
                        find_status_output_policer = unit.find('.//family/inet/policer/output')
                        if find_status_output_policer is None:
                            status_output_policer = "None"
                        else:
                            attr_output_policer = find_status_output_policer.get('inactive')
                            if attr_output_policer:
                                status_output_policer = "Inactive"
                            else:
                                status_output_policer = "Active"

                    #     #value policer input & output
                        raw_input_policer = unit.findtext('family/inet/policer/input')
                        input_policer = raw_input_policer if raw_input_policer else "None"
                        raw_output_policer = unit.findtext('family/inet/policer/output')
                        output_policer = raw_output_policer if raw_output_policer else "None"
                        
                    #     #vlan_id
                        vlan_id = unit.findtext('vlan-id')

                    # jika semua ada
                    return {
                        "status": "success",
                        "message": f"Interface {data.interface} unit {data.unit} found at device {data.hostname}. success to add",
                        "hostname": data.hostname,
                        "interface": data.interface,
                        "unit": unit_name,
                        "status_unit": status_unit,
                        "description": description,
                        "ip": ip,
                        "vlan_id": vlan_id,
                        "status_policer": status_policer,
                        "status_input_policer": status_input_policer,
                        "status_output_policer": status_output_policer,
                        "input_policer": input_policer,
                        "output_policer": output_policer,
                    }


    except (ConnectError, ConnectRefusedError, ConnectAuthError, RpcTimeoutError) as e:
            return JSONResponse(
                status_code=504,
                content={
                    "status":"failed",
                    "message":f"Cannot reach device {data.hostname}: {str(e)}",
                    "hostname": data.hostname
                }
            )

    except Exception as e:
            return JSONResponse(
                status_code=504,
                content={
                    "status":"failed",
                    "message":f"Error anomaly device {data.hostname}: {str(e)}",
                    "hostname": data.hostname  
                }
            )


#### APPS POLICER ####

class PolicerData(BaseModel):
    hostname: str
    policer_name: str
    limit_bandwidth: str   # misal "10m"
    limit_burst: str       # misal "5m"
    id_group: int
    id_user: int


@app.post("/receive-bw")
def receive_bw(data: PolicerData):
    try:
        with engine.begin() as conn:
            router = conn.execute(
                text("SELECT ip_address, logical_system FROM table_bwm_rtr WHERE hostname=:h LIMIT 1"),
                {"h": data.hostname}
            ).fetchone()

        ip_device = router.ip_address
        logical_system = router.logical_system

        # connect ke device
        with Device(host=ip_device, user=JUNIPER_USER, passwd=JUNIPER_PASS, timeout=10) as dev:
            with Config(dev, mode="exclusive") as cfg:
                if logical_system == "no":

                    ### VERIFIKASI CONFIG ###
                    filter_xml_check = etree.XML(f"""
                    <configuration>
                      <firewall>
                        <policer>
                          <name>{data.policer_name}</name>
                        </policer>
                      </firewall>
                    </configuration>
                    """)
                    cfg_get = dev.rpc.get_config(filter_xml=filter_xml_check)
                    policer_check = cfg_get.find('.//policer')
                    if policer_check is None:
                        policer_config = f"""
                            set firewall policer {data.policer_name} if-exceeding bandwidth-limit {data.limit_bandwidth}
                            set firewall policer {data.policer_name} if-exceeding burst-size-limit {data.limit_burst}
                            set firewall policer {data.policer_name} then discard
                        """
                        cfg.load(policer_config, format="set")
                        cfg.commit()

                        ### VERIFIKASI CONFIG ###
                        filter_xml = etree.XML(f"""
                        <configuration>
                          <firewall>
                            <policer>
                              <name>{data.policer_name}</name>
                            </policer>
                          </firewall>
                        </configuration>
                        """)
                        cfg_get = dev.rpc.get_config(filter_xml=filter_xml)
                        # parsing policer info
                        policer = cfg_get.find('.//policer')
                        if policer is None:
                            return JSONResponse(
                                status_code=500,
                                content={
                                    "status": "failed",
                                    "message": f"Policer {data.policer_name} not found after commit on {data.hostname}",
                                    "hostname": data.hostname

                                }
                            )

                        # ambil nilai limit bandwidth & burst
                        bw_elem = policer.find('if-exceeding/bandwidth-limit')
                        burst_elem = policer.find('if-exceeding/burst-size-limit')
                        bw_value = bw_elem.text if bw_elem is not None else "None"
                        burst_value = burst_elem.text if burst_elem is not None else "None"

                        return {
                            "status": "success",
                            "message": f"Policer {data.policer_name} configured and verified on {data.hostname}",
                            "hostname": data.hostname,
                            "policer_name": data.policer_name,
                            "limit_bandwidth": bw_value,
                            "limit_burst": burst_value,
                            "id_group": data.id_group,
                            "id_user": data.id_user
                        }
                    else:
                        return JSONResponse(
                            status_code=500,
                            content={
                                "status": "failed",
                                "message": f"policer {data.policer_name} already exist on device {data.hostname}",
                                "hostname": data.hostname

                            }
                        )

                else:
                    ### VERIFIKASI CONFIG ###
                    filter_xml_check = etree.XML(f"""
                    <configuration>
                      <logical-systems>
                        <name>{data.hostname}</name>
                        <firewall>
                            <policer>
                              <name>{data.policer_name}</name>
                            </policer>
                          </firewall>
                      </logical-systems>
                    </configuration>
                    """)
                    cfg_get = dev.rpc.get_config(filter_xml=filter_xml_check)
                    policer_check = cfg_get.find('.//policer')
                    if policer_check is None:
                        policer_config = f"""
                            set logical-systems {data.hostname} firewall policer {data.policer_name} if-exceeding bandwidth-limit {data.limit_bandwidth}
                            set logical-systems {data.hostname} firewall policer {data.policer_name} if-exceeding burst-size-limit {data.limit_burst}
                            set logical-systems {data.hostname} firewall policer {data.policer_name} then discard
                        """
                        cfg.load(policer_config, format="set")
                        cfg.commit()

                        ### VERIFIKASI CONFIG ###
                        filter_xml = etree.XML(f"""
                        <configuration>
                          <logical-systems>
                            <name>{data.hostname}</name>
                            <firewall>
                                <policer>
                                  <name>{data.policer_name}</name>
                                </policer>
                              </firewall>
                          </logical-systems>
                        </configuration>
                        """)
                        cfg_get = dev.rpc.get_config(filter_xml=filter_xml)
                        # parsing policer info
                        policer = cfg_get.find('.//policer')
                        if policer is None:
                            return JSONResponse(
                                status_code=504,
                                content={
                                    "status": "failed",
                                    "message": f"Policer {data.policer_name} not found after commit on {data.hostname}",
                                    "hostname": data.hostname
                                }
                            )

                        # ambil nilai limit bandwidth & burst
                        bw_elem = policer.find('if-exceeding/bandwidth-limit')
                        burst_elem = policer.find('if-exceeding/burst-size-limit')
                        bw_value = bw_elem.text if bw_elem is not None else "None"
                        burst_value = burst_elem.text if burst_elem is not None else "None"

                        return {
                            "status": "success",
                            "message": f"Policer {data.policer_name} configured and verified on {data.hostname}",
                            "hostname": data.hostname,
                            "policer_name": data.policer_name,
                            "limit_bandwidth": bw_value,
                            "limit_burst": burst_value,
                            "id_group": data.id_group,
                            "id_user": data.id_user
                        }
                    else:
                        return JSONResponse(
                            status_code=404,
                            content={
                                "status": "failed",
                                "message": f"policer {data.policer_name} already exist on device {data.hostname}",
                                "hostname": data.hostname

                            }
                        )
                
    except (ConnectError, ConnectRefusedError, ConnectAuthError, RpcTimeoutError) as e:
            return JSONResponse(
                status_code=504,
                content={
                    "status":"failed",
                    "message":f"Cannot reach device {data.hostname}: {str(e)}",
                    "hostname": data.hostname
                }
            )

    except Exception as e:
            return JSONResponse(
                status_code=504,
                content={
                    "status":"failed",
                    "message":f"Error anomaly device {data.hostname}: {str(e)}",
                    "hostname": data.hostname
                }
            )


#### APPS BOD ####
class BodData(BaseModel):
    hostname: str
    interface: str
    unit: int 
    description: str
    old_input_policer: str 
    old_output_policer: str
    bod_input_policer: str 
    bod_output_policer: str
    date: datetime
    id_group: int
    id_user: int

@app.post("/receive-bod")
def receive_bod(data: BodData):
    mysql_date = data.date.strftime("%Y-%m-%d %H:%M:%S")
    try:

        with engine.begin() as conn:
            router = conn.execute(
                text("SELECT ip_address, logical_system FROM table_bwm_rtr WHERE hostname=:h LIMIT 1"),
                {"h": data.hostname}
            ).fetchone()

        ip_device = router.ip_address
        logical_system = router.logical_system

        # connect ke device
        with Device(host=ip_device, user=JUNIPER_USER, passwd=JUNIPER_PASS, timeout=10) as dev:
            with Config(dev, mode="exclusive") as cfg:
                # escape semua { } yang bagian config Juniper
                if logical_system == "no":
                    bod_config = f"""
                        set interfaces {data.interface} unit {data.unit} family inet policer input {data.bod_input_policer}
                        set interfaces {data.interface} unit {data.unit} family inet policer output {data.bod_output_policer}
                    """
                    cfg.load(bod_config, format="set")
                    cfg.commit()


                    ### VERIFIKASI CONFIG ###
                    filter_xml = etree.XML(f"""
                        <configuration>
                          <interfaces>
                            <interface>
                              <name>{data.interface}</name>
                              <unit>
                                <name>{data.unit}</name>
                              </unit>
                            </interface>
                          </interfaces>
                        </configuration>
                    """)
                    cfg_get = dev.rpc.get_config(filter_xml=filter_xml)
                    input_policer = cfg_get.findtext('.//family/inet/policer/input')
                    output_policer = cfg_get.findtext('.//family/inet/policer/output')
                    if input_policer == data.bod_input_policer and output_policer == data.bod_output_policer:
                        return {
                            "status": "success",
                            "message": f"Configuration applied on router {data.hostname} at interface {data.interface} unit {data.unit}",
                            "hostname": data.hostname,
                            "description": data.description,
                            "interface": data.interface,
                            "unit": data.unit,
                            "old_input_policer": data.old_input_policer,
                            "old_output_policer": data.old_output_policer,
                            "date": mysql_date,
                            "bod_input_policer": data.bod_input_policer,
                            "bod_output_policer": data.bod_output_policer,
                            "id_group": data.id_group,
                            "id_user": data.id_user,

                        }
                    else:
                        return {
                            "status": "failed",
                            "description": data.description,
                            "message": f"Configuration failed on router {data.hostname} at interface {data.interface} unit {data.unit}",
                            "input_policer": input_policer,
                            "output_policer": output_policer,
                            "id_group": data.id_group,
                        }
                else:
                    bod_config = f"""
                        set logical-systems {data.hostname} interfaces {data.interface} unit {data.unit} family inet policer input {data.bod_input_policer}
                        set logical-systems {data.hostname} interfaces {data.interface} unit {data.unit} family inet policer output {data.bod_output_policer}
                    """
                    cfg.load(bod_config, format="set")
                    cfg.commit()


                    ### VERIFIKASI CONFIG ###
                    filter_xml = etree.XML(f"""
                        <configuration>
                            <logical-systems>
                                <name>{data.hostname}</name>
                                <interfaces>
                                    <interface>
                                      <name>{data.interface}</name>
                                        <unit>
                                            <name>{data.unit}</name>
                                        </unit>
                                    </interface>
                              </interfaces>
                            </logical-systems>
                        </configuration>
                    """)
                    cfg_get = dev.rpc.get_config(filter_xml=filter_xml)
                    input_policer = cfg_get.findtext('.//family/inet/policer/input')
                    output_policer = cfg_get.findtext('.//family/inet/policer/output')
                    if input_policer == data.bod_input_policer and output_policer == data.bod_output_policer:
                        return {
                            "status": "success",
                            "message": f"Configuration applied on router {data.hostname} at interface {data.interface} unit {data.unit}",
                            "hostname": data.hostname,
                            "description": data.description,
                            "interface": data.interface,
                            "unit": data.unit,
                            "old_input_policer": data.old_input_policer,
                            "old_output_policer": data.old_output_policer,
                            "date": mysql_date,
                            "bod_input_policer": data.bod_input_policer,
                            "bod_output_policer": data.bod_output_policer,
                            "id_group": data.id_group,
                            "id_user": data.id_user,

                        }
                    else:
                        return {
                            "status": "failed",
                            "description": data.description,
                            "message": f"Configuration failed on router {data.hostname} at interface {data.interface} unit {data.unit}",
                            "input_policer": input_policer,
                            "output_policer": output_policer,
                            "id_group": data.id_group,
                        }
                
    except (ConnectError, ConnectRefusedError, ConnectAuthError, RpcTimeoutError) as e:
            return JSONResponse(
                status_code=504,
                content={
                    "status":"failed",
                    "description": data.description,
                    "message":f"Cannot reach device {data.hostname}: {str(e)}",
                    "id_group": data.id_group, 
                }
            )

    except Exception as e:
            return JSONResponse(
                status_code=504,
                content={
                    "status":"failed",
                    "description": data.description,
                    "id_group": data.id_group,
                    "message":f"Error anomaly device {data.hostname}: {str(e)}"    
                }
            )

@app.get("/rollback-bod")
def rollback_bod():
    now = datetime.now()
    with engine.begin() as conn:
        expired_rows = conn.execute(text("""
            SELECT id, description, hostname, interface, unit_interface, old_input_policer, old_output_policer, bod_input_policer, bod_output_policer, id_group
            FROM table_bwm_bod
            WHERE status='Active' AND bod_until <= :now
        """), {"now": now}).fetchall()

        results = []

        for row in expired_rows:
            try:
                router = conn.execute(
                    text("SELECT ip_address, logical_system FROM table_bwm_rtr WHERE hostname=:h LIMIT 1"),
                    {"h": row.hostname}
                ).fetchone()

                ip_device = router.ip_address
                logical_system = router.logical_system
                with Device(host=ip_device, user=JUNIPER_USER, passwd=JUNIPER_PASS, timeout=10) as dev:
                    with Config(dev, mode="exclusive") as cfg:
                        if logical_system == "no":

                            filter_xml_check = etree.XML(f"""
                                <configuration>
                                  <interfaces>
                                    <interface>
                                      <name>{row.interface}</name>
                                      <unit>
                                        <name>{row.unit_interface}</name>
                                      </unit>
                                    </interface>
                                  </interfaces>
                                </configuration>
                            """)
                            cfg_get = dev.rpc.get_config(filter_xml=filter_xml_check)
                            input_policer_check = cfg_get.findtext('.//family/inet/policer/input')
                            output_policer_check = cfg_get.findtext('.//family/inet/policer/output')

                            if input_policer_check == row.bod_input_policer and output_policer_check == row.bod_output_policer:

                                rollback_config = f"""
                                set interfaces {row.interface} unit {row.unit_interface} family inet policer input {row.old_input_policer}
                                set interfaces {row.interface} unit {row.unit_interface} family inet policer output {row.old_output_policer}
                                """
                                cfg.load(rollback_config, format="set")
                                cfg.commit()

                                filter_xml = etree.XML(f"""
                                    <configuration>
                                      <interfaces>
                                        <interface>
                                          <name>{row.interface}</name>
                                          <unit>
                                            <name>{row.unit_interface}</name>
                                          </unit>
                                        </interface>
                                      </interfaces>
                                    </configuration>
                                """)
                                cfg_get = dev.rpc.get_config(filter_xml=filter_xml)
                                input_policer = cfg_get.findtext('.//family/inet/policer/input')
                                output_policer = cfg_get.findtext('.//family/inet/policer/output')
                                if input_policer == row.old_input_policer and output_policer == row.old_output_policer:
                                    # update status jadi Inactive
                                    conn.execute(text("""
                                        UPDATE table_bwm_bod SET status='Inactive'
                                        WHERE id=:id
                                    """), {"id": row.id})

                                    results.append({
                                        "hostname": row.hostname,
                                        "interface": row.interface,
                                        "unit": row.unit_interface,
                                        "status": "rollback success"
                                    })
                                    conn.execute(
                                        text("""
                                                INSERT INTO table_loggings (action_by, category_action, status, ip_address, agent, details, id_group, created_at)
                                                VALUES (:action_by, :category_action, :status, :ip_address, :agent, :details, :id_group, NOW())
                                        """),
                                        {
                                            "action_by": "Automation System",
                                            "category_action": "Rollback BOD",
                                            "status": "Success",
                                            "ip_address": "localhost",
                                            "agent": "backend",
                                            "details": f"Rollback for client {row.description} interface={row.interface} unit={row.unit_interface} success from BOD bandwidth(up/down)={row.bod_input_policer}/{bod.output_policer} to old bandwidth={row.old_input_policer}/{row.old_output_policer}, status change with Inactive",
                                            "id_group": {row.id_group}
                                        }
                                    )
                                else:
                                    results.append({
                                        "status": "failed",
                                    })

                            else:
                                conn.execute(
                                    text("""
                                            INSERT INTO table_loggings (action_by, category_action, status, ip_address, agent, details, id_group, created_at)
                                            VALUES (:action_by, :category_action, :status, :ip_address, :agent, :details, :id_group, NOW())
                                    """),
                                    {
                                            "action_by": "Automation System",
                                            "category_action": "Rollback BOD",
                                            "status": "Failed",
                                            "ip_address": "localhost",
                                            "agent": "backend",
                                            "details": f"Rollback for client {row.description} interface={row.interface} unit={row.unit_interface} failed because policer at BOD time {row.bod_input_policer}/{row.bod_output_policer} with existing configuration {input_policer_check}/{output_policer_check} not match, status change with CRASH",
                                            "id_group": {row.id_group}
                                    }

                                )
                                conn.execute(text("""
                                    UPDATE table_bwm_bod SET status='CRASH'
                                    WHERE id=:id
                                """), {"id": row.id})



                        #jika logical system
                        else:
                            filter_xml_check = etree.XML(f"""
                            <configuration>
                                <logical-systems>
                                    <name>{row.hostname}</name>
                                    <interfaces>
                                        <interface>
                                          <name>{row.interface}</name>
                                            <unit>
                                                <name>{row.unit_interface}</name>
                                            </unit>
                                        </interface>
                                  </interfaces>
                                </logical-systems>
                            </configuration>
                            """)
                            cfg_get = dev.rpc.get_config(filter_xml=filter_xml_check)
                            input_policer_check = cfg_get.findtext('.//family/inet/policer/input')
                            output_policer_check = cfg_get.findtext('.//family/inet/policer/output')
                            if input_policer_check == row.bod_input_policer and output_policer_check == row.bod_output_policer:
                                rollback_config = f"""
                                set logical-systems {row.hostname} interfaces {row.interface} unit {row.unit_interface} family inet policer input {row.old_input_policer}
                                set logical-systems {row.hostname} interfaces {row.interface} unit {row.unit_interface} family inet policer output {row.old_output_policer}
                                """
                                cfg.load(rollback_config, format="set")
                                cfg.commit()

                                filter_xml = etree.XML(f"""
                                <configuration>
                                    <logical-systems>
                                        <name>{row.hostname}</name>
                                        <interfaces>
                                            <interface>
                                              <name>{row.interface}</name>
                                                <unit>
                                                    <name>{row.unit_interface}</name>
                                                </unit>
                                            </interface>
                                      </interfaces>
                                    </logical-systems>
                                </configuration>
                                """)
                                cfg_get = dev.rpc.get_config(filter_xml=filter_xml)
                                input_policer = cfg_get.findtext('.//family/inet/policer/input')
                                output_policer = cfg_get.findtext('.//family/inet/policer/output')
                                if input_policer == row.old_input_policer and output_policer == row.old_output_policer:
                                    # update status jadi Inactive
                                    conn.execute(text("""
                                        UPDATE table_bwm_bod SET status='Inactive'
                                        WHERE id=:id
                                    """), {"id": row.id})

                                    results.append({
                                        "hostname": row.hostname,
                                        "interface": row.interface,
                                        "unit": row.unit_interface,
                                        "status": "rollback success"
                                    })
                                    conn.execute(
                                        text("""
                                                INSERT INTO table_loggings (action_by, category_action, status, ip_address, agent, details, id_group, created_at)
                                                VALUES (:action_by, :category_action, :status, :ip_address, :agent, :details, :id_group, NOW())
                                        """),
                                        {
                                            "action_by": "Automation System",
                                            "category_action": "Rollback BOD",
                                            "status": "Success",
                                            "ip_address": "localhost",
                                            "agent": "backend",
                                            "details": f"Rollback for client {row.description} interface={row.interface} unit={row.unit_interface} success, status change with Inactive",
                                            "id_group": {row.id_group}
                                        }
                                    )
                                else:
                                    results.append({
                                        "status": "failed",
                                    })
                            else:
                                conn.execute(
                                    text("""
                                            INSERT INTO table_loggings (action_by, category_action, status, ip_address, agent, details, id_group, created_at)
                                            VALUES (:action_by, :category_action, :status, :ip_address, :agent, :details, :id_group, NOW())
                                    """),
                                    {
                                            "action_by": "Automation System",
                                            "category_action": "Rollback BOD",
                                            "status": "Failed",
                                            "ip_address": "localhost",
                                            "agent": "backend",
                                            "details": f"Rollback for client {row.description} interface={row.interface} unit={row.unit_interface} failed because policer at BOD time {row.bod_input_policer}/{row.bod_output_policer} with existing configuration {input_policer_check}/{output_policer_check} not match, status change with CRASH",
                                            "id_group": {row.id_group}
                                    }

                                )
                                conn.execute(text("""
                                    UPDATE table_bwm_bod SET status='CRASH'
                                    WHERE id=:id
                                """), {"id": row.id})



            except (ConnectError, ConnectRefusedError, ConnectAuthError, RpcTimeoutError) as e:
                results.append({
                    "hostname": row.hostname,
                    "interface": row.interface,
                    "unit": row.unit_interface,
                    "status": f"device unreachable: {str(e)}"
                })
            except Exception as e:
                results.append({
                    "hostname": row.hostname,
                    "interface": row.interface,
                    "unit": row.unit_interface,
                    "status": f"error: {str(e)}"
                })

        return {"results": results}


class RefreshClientData(BaseModel):
    hostname: str
    interface: str
    description: str
    unit: int
    input_policer: str
    output_policer: str



@app.post("/refresh-client")
def refresh_client(data: RefreshClientData):
    try:
        with engine.begin() as conn:
            router = conn.execute(
                text("SELECT ip_address, logical_system FROM table_bwm_rtr WHERE hostname=:h LIMIT 1"),
                {"h": data.hostname}
            ).fetchone()

        ip_device = router.ip_address
        logical_system = router.logical_system

        # connect ke device
        with Device(host=ip_device, user=JUNIPER_USER, passwd=JUNIPER_PASS, timeout=10) as dev:
            with Config(dev, mode="exclusive") as cfg:
                if logical_system == "no":

                    filter_xml = etree.XML(f"""
                         <configuration>
                           <interfaces>
                             <interface>
                               <name>{data.interface}</name>
                               <unit>
                                 <name>{data.unit}</name>
                               </unit>
                             </interface>
                           </interfaces>
                         </configuration>
                    """)
                    cfg_get = dev.rpc.get_config(filter_xml=filter_xml)
                    input_policer = cfg_get.findtext('.//family/inet/policer/input')
                    output_policer = cfg_get.findtext('.//family/inet/policer/output')

                    if data.input_policer == input_policer and data.output_policer == output_policer:
                        return {
                            "status": "success",
                            "message": f"Configuration on device matches database records for client {data.description}",
                        }
                    else:
                        return {
                            "status": "failed",
                            "message": f"Configuration on device does not match database records for client {data.description}",
                        }
                else:
                    filter_xml = etree.XML(f"""
                    <configuration>
                        <logical-systems>
                            <name>{data.hostname}</name>
                            <interfaces>
                                <interface>
                                  <name>{data.interface}</name>
                                    <unit>
                                        <name>{data.unit}</name>
                                    </unit>
                                </interface>
                          </interfaces>
                        </logical-systems>
                    </configuration>
                    """)
                    cfg_get = dev.rpc.get_config(filter_xml=filter_xml)
                    input_policer = cfg_get.findtext('.//family/inet/policer/input')
                    output_policer = cfg_get.findtext('.//family/inet/policer/output')

                    if data.input_policer == input_policer and data.output_policer == output_policer:
                        return {
                            "status": "success",
                            "message": f"Configuration on device matches database records for client {data.description}",
                        }
                    else:
                        return {
                            "status": "failed",
                            "message": f"Configuration on device does not match database records for client {data.description}",
                        }

                
    except (ConnectError, ConnectRefusedError, ConnectAuthError, RpcTimeoutError) as e:
            return JSONResponse(
                status_code=504,
                content={
                    "status":"failed",
                    "message":f"Cannot reach device {data.hostname}: {str(e)}",
                    "hostname": data.hostname
                }
            )

    except Exception as e:
            return JSONResponse(
                status_code=504,
                content={
                    "status":"failed",
                    "message":f"Error anomaly device {data.hostname}: {str(e)}",
                    "hostname": data.hostname
                }
            )
