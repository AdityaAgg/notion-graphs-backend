import * as core from "@aws-cdk/core";
import * as apigateway from "@aws-cdk/aws-apigateway";
import * as lambda from "@aws-cdk/aws-lambda";
import * as path from "path";
export class NotionGraphsService extends core.Construct {
    constructor(scope: core.Construct, id: string) {
        super(scope, id);
        const handler = new lambda.Function(this, 'Function', {
            code: lambda.Code.fromAsset(__dirname + '../../../', {
                bundling: {
                    image: lambda.Runtime.PYTHON_3_6.bundlingDockerImage,
                    user: 'root',
                    command: [
                        'bash', '-c', `
              pip install -r requirements.txt -t /asset-output &&
              (yum -q list installed rsync &>/dev/null || yum install -y rsync) &&
              rsync -au . /asset-output --exclude notion-graphs-backend-infra
              `,
                    ],
                },
            }),
            runtime: lambda.Runtime.PYTHON_3_6,
            handler: 'app.healthy_route',
        });

        const api = new apigateway.RestApi(this, "notion-graphs-api", {
            restApiName: "Notion Graphs Service",
            description: "This service serves for Notion Graphs."
        });

        const getNotionGraphsIntegration = new apigateway.LambdaIntegration(handler, {
            requestTemplates: { "application/json": '{ "statusCode": "200" }' }
        });

        api.root.addMethod("GET", getNotionGraphsIntegration); // GET /
    }
}