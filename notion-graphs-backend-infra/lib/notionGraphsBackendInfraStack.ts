import * as cdk from '@aws-cdk/core';
import * as notionGraphsService from '../lib/notionGraphsService';

export class NotionGraphsBackendInfraStack extends cdk.Stack {
  constructor(scope: cdk.Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);
    new notionGraphsService.NotionGraphsService(this, 'Notion Graphs');
    // The code that defines your stack goes here
  }
}
