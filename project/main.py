from datetime import datetime
import boto3
from botocore.client import BaseClient
from botocore import exceptions
from credentials import ACCESS_KEY, SECRET_KEY
from dataclasses import dataclass, field
from typing import List, Dict, Any
from flask import Blueprint, render_template
from flask_login import login_required, current_user
import logging
from . import db


#  Flask app declaration
main = Blueprint('main', __name__)

logger = logging.getLogger(__name__)
syslog = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s %(levelname)s %(app_name)s : %(message)s')
syslog.setFormatter(formatter)
logger.setLevel(logging.INFO)
logger.addHandler(syslog)

extra_log = {'app_name': 'App logging'}
logger = logging.LoggerAdapter(logger, extra_log)


#  routing for mian page of the app
@main.route('/')
def index():
    return render_template('index.html')


#  routing for the logged user page with the ec2 results
@main.route('/profile')
@login_required
def profile():
    instances = ServerDisplayer().run()
    return render_template('profile.html', name=current_user.name, instances=instances)


@dataclass
class InstanceIds:
    image_id: str
    instance_id: str
    kernel_id: str
    vpc_id: str
    subnet_id: str


@dataclass
class PlatformDetails:
    operating_system: str


@dataclass
class IpAddresses:
    public_ip: str
    private_ip_address: str


@dataclass
class DNS_Settings:
    public_dns_name: str
    private_dns_name: str


@dataclass
class NetworkSettings:
    ip_addresses: IpAddresses
    dns_settings: DNS_Settings
    subnet_id: str


@dataclass
class Status:
    status: str
    code: str


@dataclass
class Description:
    instance_description: str


@dataclass
class LaunchTime:
    launch_time: datetime


@dataclass
class Tags:
    instance_tags: List[Dict[str, str]]


@dataclass
class Specs:
    cpu_details: Dict[str, int]
    ram_details: str
    instance_type: str


@dataclass
class SecurityGroups:
    security_groups: List[Dict[str, str]]


@dataclass
class Tokens:
    client_tokens: str


class SessionCreator:
    def __init__(self, boto_client=None):
        self.boto_client = boto_client

    def extract_all_regions(self) -> list:
        try:
            #  In order to find instances with the relevant credentials in every AWS region,
            #  I created a list comprehension of all AWS regions
            simple_client = boto3.client('ec2') if not self.boto_client else self.boto_client
            all_regions = [region['RegionName']
                           for region in simple_client.describe_regions()['Regions']]
            logger.info(f'There are {len(all_regions)} regions in AWS')
            return all_regions
        except exceptions.ClientError:
            logger.error('AWS regions are not available, please check your boto client and try again')
        except exceptions.ConnectionError or exceptions.ConnectTimeoutError:
            logger.error('Something is wrong with your network connection, please check it')

    def create_session(self) -> dict:
        legitimate_instances = dict()
        for region in self.extract_all_regions():
            try:
                # for each region a new session is created. If there are no ec2 instances in region, an error is logged
                session = boto3.Session(
                    aws_access_key_id=ACCESS_KEY,
                    aws_secret_access_key=SECRET_KEY,
                    region_name=region
                )
                client = session.client('ec2')
                instance_id = client.describe_instances()['Reservations'][0]['Instances'][0]['InstanceId']
                ec2 = session.resource('ec2')
                legitimate_instances[region] = ec2.Instance(instance_id)
                logger.info(f'Region {region} has ec2 candidate instances')
            except exceptions.ClientError:
                logger.error(f"Region {region} has no instances in that session")
            except exceptions.NoCredentialsError or exceptions.CredentialRetrievalError:
                logger.error('EC2 instances are not available, please check your credentials')
            except exceptions.ValidationError:
                logger.error('Something went wrong with your session, please recheck and try again')

        return legitimate_instances


@dataclass
class ProcessInstanceData:
    valid_ec2_instances: Dict[str, Any] = field(default_factory=dict)
    instances_dict: Dict[str, Any] = field(default_factory=dict)

    def extract_data(self) -> dict:
        # Extracting the data and add it to output dictionary that will be displayed to user
        for region, ec2_client in self.valid_ec2_instances.items():
            instance_id = ec2_client.id
            self.instances_dict[instance_id] = {"Placement region": region}
            logger.info(f"Data for ec2 {instance_id} at region {region}")
            instance_ids = InstanceIds(ec2_client.image_id, ec2_client.instance_id,
                                       ec2_client.kernel_id, ec2_client.vpc_id,
                                       ec2_client.subnet_id)
            self.instances_dict[instance_id]["InstanceIds"] = instance_ids
            logger.info(f"Instance_ids data for ec2 {instance_id}")

            platform_details = PlatformDetails(ec2_client.platform_details)
            self.instances_dict[instance_id]["PlatformDetails"] = platform_details
            logger.info(f"Platform details data for ec2 {instance_id}")

            status = Status(ec2_client.state, ec2_client.product_codes)
            self.instances_dict[instance_id]["Status"] = status
            logger.info(f"Status data for ec2 {instance_id}")

            launch_time = LaunchTime(ec2_client.launch_time)
            self.instances_dict[instance_id]["LaunchTime"] = launch_time
            logger.info(f"Launch Time data for ec2 {instance_id}")

            tags = Tags(ec2_client.tags)
            self.instances_dict[instance_id]["Tags"] = tags
            logger.info(f"Tags data for ec2 {instance_id}")

            specs = Specs(ec2_client.cpu_options, ec2_client.ramdisk_id, ec2_client.instance_type)
            self.instances_dict[instance_id]["Specs"] = specs
            logger.info(f"Specs data for ec2 {instance_id}")

            security_groups = SecurityGroups(ec2_client.security_groups)
            self.instances_dict[instance_id]["SecurityGroups"] = security_groups
            logger.info(f"Security Groups data for ec2 {instance_id}")

            ip_addresses = IpAddresses(ec2_client.public_ip_address,
                                       ec2_client.private_ip_address)
            dns_settings = DNS_Settings(ec2_client.public_dns_name, ec2_client.private_dns_name)
            network_settings = NetworkSettings(ip_addresses, dns_settings, ec2_client.subnet_id)
            self.instances_dict[instance_id]["NetworkSettings"] = network_settings
            logger.info(f"Network Settings data for ec2 {instance_id}")

            tokens = Tokens(ec2_client.client_token)
            self.instances_dict[instance_id]["Tokens"] = tokens
            logger.info(f"Tokens data for ec2 {instance_id}")
        return self.instances_dict


class ServerDisplayer:
    def __init__(self) -> None:
        self.session = SessionCreator()

    def run(self):
        return ProcessInstanceData(self.session.create_session()).extract_data()
