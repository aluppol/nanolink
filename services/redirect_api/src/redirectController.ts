import { FastifyInstance } from "fastify"
import { FromSchema } from "json-schema-to-ts";
import { UrlService } from "./services";

const redirectSchema = {
    type: 'object',
    properties: {
        shortUrl: { 
        type: 'string', 
        minLength: 6,
        maxLength: 6, // Potentially will be increased
        pattern: '^[a-zA-Z0-9]+$',
      },
    },
    required: ['shortUrl']
} as const; // Use "as const" to infer the literal type

type RedirectParams = FromSchema<typeof redirectSchema>;

export async function redirectController(fastify: FastifyInstance, options: any) {
    fastify.get<{ Params: RedirectParams }>(
        "/:shortUrl",
        {
            schema: {
                params: redirectSchema,
            }
        },
        async (req, res) => {
            const { shortUrl } = req.params;
            const urlService = fastify.diContainer.resolve<UrlService>('urlService');
            
            try {
                const longUrl = await urlService.getLongUrl(shortUrl, req)
                if (longUrl) {
                    res.redirect(302, longUrl);
                } else {
                    res.status(404).send({ error: 'URL not found' });
                }
            } catch (err) {
                fastify.log.error(err);
              res.status(500).send({ error: 'Internal Server Error' });
            }
        },
        
    )
}