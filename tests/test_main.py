from project.main import SessionCreator, ProcessInstanceData, ServerDisplayer


# SessionCreator Tests
def test_session_construction():
    assert SessionCreator()


def test_extract_all_regions():
    aws_regions = ['eu-north-1', 'ap-south-1', 'eu-west-3', 'eu-west-2', 'eu-west-1', 'ap-northeast-3',
                   'ap-northeast-2', 'me-south-1', 'ap-northeast-1', 'sa-east-1', 'ca-central-1', 'ap-east-1',
                   'ap-southeast-1', 'ap-southeast-2', 'eu-central-1', 'us-east-1', 'us-east-2', 'us-west-1',
                   'us-west-2']
    assert SessionCreator().extract_all_regions() == aws_regions
    assert type(SessionCreator().extract_all_regions()) == list


def test_create_session():
    session = SessionCreator()
    new_session = session.create_session()
    assert len(new_session) == 2
    assert type(new_session) == dict
    assert 'us-east-2' in new_session and \
           'us-west-2' in new_session

    assert "ap-south-1" not in new_session


# ProcessInstanceData
def test_processor_construction():
    assert ProcessInstanceData()


def test_extract_data():
    session = SessionCreator()
    preferences = ['VpcId', 'ImageId', 'InstanceType']
    processor = ProcessInstanceData(session.create_session(), preferences)
    result = processor.extract_data()
    is_exists = False
    for key, item in result.items():
        for k, v in item.items():
            if k == 'InstanceType' and v == 't2.micro':
                is_exists = True
                break
        assert is_exists
        is_exists = False
