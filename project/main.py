import boto3
import botocore
from .credentials import ACCESS_KEY, SECRET_KEY
from pprint import pprint
from dataclasses import dataclass, field
from typing import List, Dict
from flask import Blueprint, render_template
from flask_login import login_required, current_user
from . import db

main = Blueprint('main', __name__)


@main.route('/')
def index():
    return render_template('index.html')


@main.route('/profile')
@login_required
def profile():
    param_list = ['ImageId',
                  'VpcId', 'InstanceType', 'NetworkInterfaces', 'ClientToken',
                  'State', 'PlatformDetails', 'Tags', 'LaunchTime',
                  'PrivateDnsName', 'SecurityGroups', 'PublicDnsName',
                  'BlockDeviceMappings']
    instances = ServerDisplayer(param_list).run()
    return render_template('profile.html', name=current_user.name, instances=instances)


@dataclass
class SessionCreator:

    @staticmethod
    def extract_all_regions() -> list:
        simple_client = boto3.client('ec2')
        all_regions = [region['RegionName']
                       for region in simple_client.describe_regions()['Regions']]
        print(all_regions)
        return all_regions

    def create_session(self) -> dict:
        legitimate_instances = {}
        for region in self.extract_all_regions():
            try:
                session = boto3.Session(
                    aws_access_key_id=ACCESS_KEY,
                    aws_secret_access_key=SECRET_KEY,
                    region_name=region
                )

                client = session.client('ec2')
                client.describe_instances()
                legitimate_instances[region] = client
            except botocore.exceptions.ClientError:
                pass
        return legitimate_instances


@dataclass
class ProcessInstanceData:
    valid_ec2_instances: Dict = field(default_factory=dict)
    data_to_pull: List[str] = field(default_factory=list)
    instances_dict: Dict = field(default_factory=dict)

    def extract_data(self) -> dict:
        for region, ec2_client in self.valid_ec2_instances.items():
            instance_id = ec2_client.describe_instances(
            )['Reservations'][0]['Instances'][0]['InstanceId']
            self.instances_dict[instance_id] = {"Placement region": region}
            ec2_data = ec2_client.describe_instances()
            for param in self.data_to_pull:
                self.instances_dict[instance_id][param] = ec2_data['Reservations'][0]['Instances'][0][param]

            pprint(self.instances_dict[instance_id])
        return self.instances_dict


class ServerDisplayer:
    def __init__(self, list_of_params: list) -> None:
        self.params = list_of_params
        self.session = SessionCreator()

    def run(self):
        return ProcessInstanceData(self.session.create_session(), self.params).extract_data()
