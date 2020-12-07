#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from '@aws-cdk/core';
import { NotionGraphsBackendInfraStack } from '../lib/notionGraphsBackendInfraStack';

const app = new cdk.App();
new NotionGraphsBackendInfraStack(app, 'NotionGraphsBackendInfraStack');
